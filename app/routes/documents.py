from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, Query, Body
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
import logging
import time
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.services.storage_service import S3StorageService
from app.utils.performance_logger import api_perf_logger

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, DocumentCreate, DocumentAnalysisResponse
from app.services.auth_service import get_current_active_user
from app.services.document_service import document_service
from app.services.activity_service import log_activity

# Set up logging
logger = logging.getLogger(__name__)

# Initialize S3 service if enabled
use_s3 = os.getenv('USE_S3_STORAGE', 'false').lower() == 'true'
s3_storage = S3StorageService() if use_s3 else None
logger.info(f"Document routes initialized with S3 storage: {use_s3}")

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={401: {"description": "Unauthorized"}},
)

@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    doc_type: str = Form(...),
    tag: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a document
    """
    # Start performance timer
    timer_id = api_perf_logger.start_timer("upload_document", {
        "user_id": current_user.id,
        "file_name": file.filename
    })
    
    try:
        # Validate document type
        valid_doc_types = ["repo", "template", "legal", "real_estate", "contract", "lease", "other"]  # Accept multiple document types
        if doc_type not in valid_doc_types:
            logger.warning(f"Invalid document type: {doc_type}")
            raise HTTPException(status_code=400, detail=f"Invalid document type. Must be one of: {', '.join(valid_doc_types)}")
        
        # Validate file extension
        allowed_extensions = [".pdf", ".docx", ".doc", ".csv", ".xlsx", ".xls", ".txt", ".json"]
        file_ext = f".{file.filename.split('.')[-1].lower()}"
        if file_ext not in allowed_extensions:
            logger.warning(f"Invalid file extension: {file_ext}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Get client IP
        client_host = request.client.host if request.client else None
        
        # Process document
        document = document_service.process_document(
            db=db,
            file=file,
            user_id=current_user.id,
            title=title,
            description=description,
            doc_type=doc_type,
            client_ip=client_host,
            tag=tag
        )
        
        # Stop performance timer
        api_perf_logger.stop_timer(timer_id, {
            "document_id": document.id,
            "status": document.status
        })
        
        logger.info(f"Document upload completed: {document.id} by user {current_user.id}")
        
        # If the document is partially processed, add a warning header
        if document.status == "partially_processed":
            logger.warning(f"Document {document.id} was only partially processed due to size/complexity")
            
        return document
        
    except Exception as e:
        api_perf_logger.log_operation_failed("upload_document", e)
        logger.error(f"Error uploading document: {e}")
        raise

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    doc_type: Optional[str] = None,
    include_templates: bool = False,
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List user's documents with optional filtering
    By default, documents tagged as 'template' are excluded from the results
    Use include_templates=True to include template documents in the results
    """
    timer_id = api_perf_logger.start_timer("list_documents", {
        "user_id": current_user.id,
        "skip": skip,
        "limit": limit
    })
    
    try:
        documents = document_service.get_user_documents(db, current_user.id, skip, limit)
        
        # Apply status filter if provided
        if status:
            documents = [doc for doc in documents if doc.status == status]
        
        # Apply doc_type filter if provided
        if doc_type:
            documents = [doc for doc in documents if doc.doc_type == doc_type]
            
        # Apply tag filter if provided, otherwise exclude templates by default
        if tag:
            documents = [doc for doc in documents if doc.tag == tag]
        elif not include_templates:
            documents = [doc for doc in documents if doc.tag != "template"]
        
        api_perf_logger.stop_timer(timer_id, {
            "document_count": len(documents)
        })
        
        logger.info(f"Listed {len(documents)} documents for user {current_user.id}")
        return documents
        
    except Exception as e:
        api_perf_logger.log_operation_failed("list_documents", e)
        logger.error(f"Error listing documents: {e}")
        raise

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific document
    """
    timer_id = api_perf_logger.start_timer("get_document", {
        "user_id": current_user.id,
        "document_id": document_id
    })
    
    try:
        document = document_service.get_document_by_id(db, document_id, current_user.id)
        
        api_perf_logger.stop_timer(timer_id)
        logger.info(f"Retrieved document {document_id} for user {current_user.id}")
        return document
        
    except Exception as e:
        api_perf_logger.log_operation_failed("get_document", e, details={"document_id": document_id})
        logger.error(f"Error retrieving document {document_id}: {e}")
        raise

@router.get("/{document_id}/analysis", response_model=Dict[str, Any])
async def get_document_analysis(
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get document analysis and metadata
    """
    timer_id = api_perf_logger.start_timer("get_document_analysis", {
        "user_id": current_user.id,
        "document_id": document_id
    })
    
    try:
        document = document_service.get_document_by_id(db, document_id, current_user.id)
        
        if not document.ai_analysis:
            logger.warning(f"Analysis not available for document {document_id}")
            api_perf_logger.stop_timer(timer_id, {"status": "not_available"})
            raise HTTPException(status_code=404, detail="Analysis not available for this document")
        
        try:
            analysis = json.loads(document.ai_analysis)
            
            api_perf_logger.stop_timer(timer_id, {"status": "success"})
            logger.info(f"Retrieved analysis for document {document_id}")
            
            # Check if this is a partially processed document
            if analysis.get("partial_processing"):
                # Return with a warning header
                response = JSONResponse(content=analysis)
                response.headers["X-Processing-Status"] = "partial"
                response.headers["X-Processing-Stage"] = analysis.get("processing_stage", "unknown")
                return response
            
            return analysis
        
        except json.JSONDecodeError:
            logger.error(f"Error parsing analysis JSON for document {document_id}")
            api_perf_logger.log_operation_failed("get_document_analysis", 
                                             Exception("JSON decode error"), 
                                             details={"document_id": document_id})
            raise HTTPException(status_code=500, detail="Error retrieving analysis")
            
    except HTTPException:
        # Don't log HTTPExceptions, just re-raise them
        raise
    except Exception as e:
        api_perf_logger.log_operation_failed("get_document_analysis", e, 
                                          details={"document_id": document_id})
        logger.error(f"Error getting document analysis for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving analysis: {str(e)}")

@router.post("/{document_id}/transform-with-templates", response_model=Dict[str, Any])
async def transform_document_with_templates(
    document_id: int,
    template_input_id: int = Body(...),
    template_output_id: int = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Transform a document using template input and output examples
    
    This endpoint takes:
    - A document to transform (document_id)
    - A template input document (similar format to the input document)
    - A template output document (desired format for the output)
    
    The service will process these documents and return a transformed version
    of the input document formatted like the template output.
    """
    timer_id = api_perf_logger.start_timer("transform_document_with_templates", {
        "user_id": current_user.id,
        "document_id": document_id,
        "template_input_id": template_input_id,
        "template_output_id": template_output_id
    })
    
    start_time = time.time()
    logger.info(f"Transform request received for document {document_id} with templates {template_input_id} and {template_output_id}")
    
    try:
        # Verify all documents exist and user has access
        logger.info(f"Verifying document {document_id}")
        document = document_service.get_document_by_id(db, document_id, current_user.id)
        logger.info(f"Document {document_id} verified: {document.title}")
        
        logger.info(f"Verifying template input {template_input_id}")
        template_input = document_service.get_document_by_id(db, template_input_id, current_user.id)
        logger.info(f"Template input {template_input_id} verified: {template_input.title}")
        
        logger.info(f"Verifying template output {template_output_id}")
        template_output = document_service.get_document_by_id(db, template_output_id, current_user.id)
        logger.info(f"Template output {template_output_id} verified: {template_output.title}")
        
        # Verify templates are actually tagged as templates
        logger.info(f"Checking template input tag: {template_input.tag}")
        if template_input.tag != "template":
            logger.warning(f"Document {template_input_id} is not a template")
            raise HTTPException(status_code=400, detail="The input template document is not tagged as a template")
        
        logger.info(f"Checking template output tag: {template_output.tag}")
        if template_output.tag != "template":
            logger.warning(f"Document {template_output_id} is not a template")
            raise HTTPException(status_code=400, detail="The output template document is not tagged as a template")
        
        # Perform the transformation
        logger.info(f"Calling transform_document_with_templates service method")
        result = document_service.transform_document_with_templates(
            db=db,
            document=document,
            template_input=template_input,
            template_output=template_output,
            user_id=current_user.id
        )
        
        # Handle different result status types
        if result.get("status") == "retry_required":
            processing_time = time.time() - start_time
            api_perf_logger.stop_timer(timer_id, {
                "status": "retry_required",
                "processing_time": processing_time
            })
            
            # Return a specific status code for retry requests
            response = JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "status": "retry_required",
                    "message": result.get("message", "Document too complex for synchronous processing"),
                    "detail": result.get("error", "Processing time limit exceeded"),
                    "document_id": document_id
                }
            )
            return response
        
        # Check if there was a timeout warning
        if result.get("timeout_warning"):
            # Set header to indicate timeout
            processing_time = time.time() - start_time
            api_perf_logger.stop_timer(timer_id, {
                "status": "timeout_warning",
                "processing_time": processing_time
            })
            
            # Return with a timeout warning header
            response = JSONResponse(content=result)
            response.headers["X-Processing-Status"] = "timeout"
            response.headers["X-Processing-Warning"] = result.get("timeout_warning")
            return response
        
        # Normal successful response
        processing_time = time.time() - start_time
        api_perf_logger.stop_timer(timer_id, {
            "status": "success",
            "processing_time": processing_time
        })
        
        logger.info(f"Transformation completed successfully in {processing_time:.2f}s")
        return result
        
    except HTTPException as he:
        logger.error(f"HTTP exception in transform_document_with_templates: {he.detail}")
        api_perf_logger.log_operation_failed("transform_document_with_templates", he, 
                                          details={"document_id": document_id})
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in transform_document_with_templates: {str(e)}")
        api_perf_logger.log_operation_failed("transform_document_with_templates", e, 
                                          details={"document_id": document_id})
        raise HTTPException(status_code=500, detail=f"Error processing transformation: {str(e)}")

@router.post("/generate", response_model=Dict[str, Any])
async def create_document(
    request: Request,
    template_type: str = Form(...),
    input_data: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new document from provided content
    """
    timer_id = api_perf_logger.start_timer("create_document", {
        "user_id": current_user.id,
        "template_type": template_type
    })
    
    try:
        # Validate template type
        valid_template_types = ["deposition"]  # Only deposition template is allowed
        if template_type not in valid_template_types:
            logger.warning(f"Invalid template type: {template_type}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid template type. Must be: {valid_template_types[0]}"
            )
        
        # Parse input data
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON input data")
            raise HTTPException(status_code=400, detail="Invalid JSON input data")
        
        # Get client IP
        client_host = request.client.host if request.client else None
        
        try:
            # Generate document
            document, generated_text = document_service.generate_document(
                db=db,
                user_id=current_user.id,
                template_type=template_type,
                input_data=data,
                title=title,
                description=description,
                content=content,
                client_ip=client_host
            )
            
            api_perf_logger.stop_timer(timer_id, {
                "document_id": document.id,
                "status": "success"
            })
            
            logger.info(f"Document generated: {document.id} by user {current_user.id}")
            return {
                "document_id": document.id,
                "content": generated_text
            }
        
        except Exception as e:
            logger.error(f"Error generating document: {e}")
            api_perf_logger.log_operation_failed("create_document", e)
            raise HTTPException(status_code=500, detail=f"Error generating document: {str(e)}")
            
    except HTTPException:
        # Don't log HTTPExceptions, just re-raise them
        raise
    except Exception as e:
        api_perf_logger.log_operation_failed("create_document", e)
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating document: {str(e)}")

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    request: Request,
    document_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document
    """
    timer_id = api_perf_logger.start_timer("delete_document", {
        "user_id": current_user.id,
        "document_id": document_id
    })
    
    try:
        client_host = request.client.host if request.client else None
        
        document_service.delete_document(
            db=db,
            document_id=document_id,
            user_id=current_user.id,
            client_ip=client_host
        )
        
        api_perf_logger.stop_timer(timer_id, {"status": "success"})
        logger.info(f"Document {document_id} deleted successfully")
        
        return None
        
    except Exception as e:
        api_perf_logger.log_operation_failed("delete_document", e, 
                                          details={"document_id": document_id})
        logger.error(f"Error deleting document {document_id}: {e}")
        raise

@router.get("/downloads/{filename}")
async def download_file(
    request: Request,
    filename: str,
    token: str = Query(None),
    expires: int = Query(None),
    user_id: int = Query(None),
    db: Session = Depends(get_db)
):
    """
    Download a generated or transformed file
    
    Args:
        filename: Name of the file to download (just the filename, not path)
        token: Optional signed token for authentication
        expires: Optional expiration timestamp
        user_id: Optional user ID associated with the token
        
    Returns:
        FileResponse or RedirectResponse: The file download or redirect to S3
    """
    timer_id = api_perf_logger.start_timer("download_file", {
        "filename": filename
    })
    
    try:
        # If token is provided, validate signature-based auth instead of JWT
        if token and expires and user_id:
            logger.info(f"Using signed URL authentication for file: {filename}")
            # Check if token has expired
            if int(expires) < datetime.now().timestamp():
                logger.warning(f"Expired download token for file: {filename}")
                api_perf_logger.stop_timer(timer_id, {"status": "expired_token"})
                raise HTTPException(status_code=401, detail="Download link expired")
                
            # Validate token signature
            from app.services.auth_service import SECRET_KEY
            import hashlib
            import hmac
            
            # Recreate the signature to verify
            expected_signature = hmac.new(
                SECRET_KEY.encode(), 
                f"{filename}:{user_id}:{expires}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(token, expected_signature):
                logger.warning(f"Invalid download token for file: {filename}")
                api_perf_logger.stop_timer(timer_id, {"status": "invalid_token"})
                raise HTTPException(status_code=401, detail="Invalid download token")
                
            logger.info(f"Signed URL authentication successful for user: {user_id}")
            
        else:
            # Fall back to using the authenticated user from the JWT token
            logger.info("Signed URL params not provided, using JWT authentication")
            from app.services.auth_service import get_current_active_user, oauth2_scheme
            
            try:
                # Extract the JWT token from the Authorization header
                jwt_token = await oauth2_scheme(request)
                # First get the current user, then check if it's active
                from app.services.auth_service import get_current_user
                current_user = await get_current_user(token=jwt_token, db=db)
                # get_current_active_user would be called internally by the dependency system
                # but we need to check manually since we're bypassing the dependency system
                if not current_user.is_active:
                    api_perf_logger.stop_timer(timer_id, {"status": "inactive_user"})
                    raise HTTPException(status_code=403, detail="Inactive user")
                user_id = current_user.id
                logger.info(f"JWT authentication successful for user: {user_id}")
            except HTTPException as e:
                logger.warning(f"JWT authentication failed: {str(e)}")
                api_perf_logger.stop_timer(timer_id, {"status": "auth_failed"})
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Security check - ensure filename doesn't contain path traversal
        if os.path.sep in filename or '..' in filename:
            logger.warning(f"Invalid filename with path traversal attempt: {filename}")
            api_perf_logger.stop_timer(timer_id, {"status": "invalid_filename"})
            raise HTTPException(status_code=400, detail="Invalid filename")
            
        # Log the download activity
        log_activity(
            db=db,
            action="file_downloaded",
            user_id=user_id,
            description=f"File downloaded: {filename}",
            details={"filename": filename, "storage": "s3" if use_s3 else "local"}
        )
        
        if use_s3:
            # For S3 storage, generate a presigned URL and redirect
            object_key = f"uploads/{user_id}/{filename}"
            
            # Generate presigned URL for S3 object
            presigned_url = s3_storage.get_file_url(
                object_key=object_key, 
                expires_in=3600  # URL valid for 1 hour
            )
            
            # Redirect to the presigned URL
            logger.info(f"Redirecting to S3 presigned URL for file: {object_key}")
            api_perf_logger.stop_timer(timer_id, {"status": "s3_redirect"})
            return RedirectResponse(url=presigned_url)
        else:
            # For local storage, serve the file directly
            user_dir = os.path.join("uploads", str(user_id))
            file_path = os.path.join(user_dir, filename)
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                api_perf_logger.stop_timer(timer_id, {"status": "file_not_found"})
                raise HTTPException(status_code=404, detail="File not found")
            
            # Return the file
            logger.info(f"Serving local file for download: {file_path}")
            api_perf_logger.stop_timer(timer_id, {"status": "local_file"})
            return FileResponse(
                path=file_path, 
                filename=filename,
                media_type="application/octet-stream"
            )
        
    except HTTPException:
        # Don't log HTTPExceptions, just re-raise them
        raise
    except Exception as e:
        logger.error(f"Error serving file: {e}")
        api_perf_logger.log_operation_failed("download_file", e, 
                                         details={"filename": filename})
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")