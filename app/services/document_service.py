import os
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, BinaryIO, List, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.models.document import Document
from app.utils.document_processor import DocumentProcessor, convert_numpy_to_python
from app.services.activity_service import log_activity
from app.services.openai_service import openai_service
from app.utils.performance_logger import document_perf_logger

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Set up logging
logger = logging.getLogger(__name__)

# Create document processor instance
document_processor = DocumentProcessor(upload_dir="uploads")

# Maximum processing time in seconds - aligns with Heroku's 30s timeout
MAX_PROCESSING_TIME = 25  # 25 seconds, allowing a 5 second buffer

class DocumentService:
    """Service for document processing and management"""
    
    @staticmethod
    def process_document(
        db: Session,
        file: UploadFile,
        user_id: int,
        title: str,
        description: Optional[str],
        doc_type: str,
        client_ip: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Document:
        """Process a document (save, extract text, analyze)

        Args:
            db: Database session
            file: The uploaded file
            user_id: ID of the user uploading the file
            title: Document title
            description: Document description
            doc_type: Type of document
            client_ip: Client IP address for activity logging

        Returns:
            Document: The created document record

        Raises:
            HTTPException: If processing fails
        """
        # Start performance timer
        timer_id = document_perf_logger.start_timer("process_document", {
            "user_id": user_id,
            "file_name": file.filename,
            "file_size": file.file.tell()
        })
        
        try:
            # Step 1: Reset file position and read file content
            file.file.seek(0)  # Reset file position to beginning
            file_content = file.file.read()
            
            # Validate file content
            if not file_content:
                logger.error(f"File content is empty for file: {file.filename}")
                raise ValueError(f"Empty or invalid file: {file.filename}")
            
            # Step 2: Save file to disk
            file_path = document_processor.save_file(file_content, file.filename, user_id)
            
            # Step 3: Create document record
            document = Document(
                user_id=user_id,
                title=title,
                description=description,
                doc_type=doc_type,
                status="uploaded",
                original_filename=file.filename,
                file_path=file_path,
                tag=tag
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Log activity
            log_activity(
                db=db,
                action="document_uploaded",
                user_id=user_id,
                description=f"Document uploaded: {title}",
                ip_address=client_ip,
                details={
                    "document_id": document.id,
                    "doc_type": doc_type,
                    "filename": file.filename
                }
            )
            
            # Step 4: Start processing synchronously
            # Modified to track processing time and handle timeout gracefully
            DocumentService._process_document_content(db, document, file_path, client_ip)
            
            logger.info(f"Document processing started: {document.id}")
            
            # Track performance and return result
            document_perf_logger.stop_timer(timer_id, {
                "document_id": document.id,
                "status": document.status
            })
            
            return document
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing document: {e}")
            document_perf_logger.log_operation_failed("process_document", e)
            raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    
    @staticmethod
    def _process_document_content(
        db: Session, 
        document: Document, 
        file_path: str,
        client_ip: Optional[str] = None
    ) -> None:
        """
        Process the document content (extract text, metadata) with timeout handling
        
        Args:
            db: Database session
            document: Document record
            file_path: Path to the document file
            client_ip: Client IP address for activity logging
        """
        # Start performance timer
        timer_id = document_perf_logger.start_timer("process_document_content", {
            "document_id": document.id,
            "file_path": file_path
        })
        
        try:
            # Update status to processing
            document.status = "processing"
            db.commit()
            
            # Record start time to enforce timeout
            start_time = time.time()
            
            # Extract text content
            text_extraction_timer = document_perf_logger.start_timer("extract_text", {
                "document_id": document.id,
                "file_path": file_path
            })
            
            text_content = document_processor.extract_text(file_path)
            document.file_content = text_content
            db.commit()
            
            # Stop text extraction timer
            document_perf_logger.stop_timer(text_extraction_timer)
            
            # Check if we're approaching timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > MAX_PROCESSING_TIME:
                document_perf_logger.log_threshold_exceeded("process_document_content", 
                                                         MAX_PROCESSING_TIME,
                                                         {"document_id": document.id,
                                                          "elapsed_time": elapsed_time})
                # If we're approaching timeout, set status to partially processed
                # and return to avoid Heroku timeout
                document.status = "partially_processed"
                document.ai_analysis = json.dumps({
                    "warning": "Processing exceeded time limit",
                    "partial_processing": True,
                    "processing_stage": "text_extraction_completed",
                    "processing_time_seconds": round(elapsed_time, 2)
                })
                db.commit()
                
                # Log activity for partial processing
                log_activity(
                    db=db,
                    action="document_partially_processed",
                    user_id=document.user_id,
                    description=f"Document partially processed: {document.title}",
                    ip_address=client_ip,
                    details={
                        "document_id": document.id,
                        "processing_time": round(elapsed_time, 2),
                        "reason": "Processing time limit exceeded"
                    }
                )
                
                document_perf_logger.stop_timer(timer_id, {
                    "document_id": document.id,
                    "status": "partially_processed",
                    "reason": "timeout"
                })
                
                logger.warning(f"Document processing timeout: {document.id} - stopped after {elapsed_time:.2f}s")
                return
            
            # Extract metadata (continue only if we have time)
            metadata_timer = document_perf_logger.start_timer("extract_metadata", {
                "document_id": document.id
            })
            
            metadata = document_processor.extract_metadata(file_path)
            document_structure = document_processor.get_document_structure(file_path)
            
            # Stop metadata timer
            document_perf_logger.stop_timer(metadata_timer)
            
            # Check timeout again
            elapsed_time = time.time() - start_time
            if elapsed_time > MAX_PROCESSING_TIME:
                document_perf_logger.log_threshold_exceeded("process_document_content", 
                                                         MAX_PROCESSING_TIME,
                                                         {"document_id": document.id,
                                                          "elapsed_time": elapsed_time})
                # Set status to partially processed
                document.status = "partially_processed"
                
                # Combine metadata and structure
                combined_metadata = {
                    "metadata": metadata,
                    "structure_info": document_structure,
                    "warning": "Processing exceeded time limit",
                    "partial_processing": True,
                    "processing_stage": "metadata_extraction_completed",
                    "processing_time_seconds": round(elapsed_time, 2)
                }
                
                # Convert any NumPy types to Python native types for JSON serialization
                serializable_analysis = convert_numpy_to_python(combined_metadata)
                
                # Update document with analysis results
                document.ai_analysis = json.dumps(serializable_analysis)
                db.commit()
                
                # Log activity for partial processing
                log_activity(
                    db=db,
                    action="document_partially_processed",
                    user_id=document.user_id,
                    description=f"Document partially processed: {document.title}",
                    ip_address=client_ip,
                    details={
                        "document_id": document.id,
                        "processing_time": round(elapsed_time, 2),
                        "reason": "Processing time limit exceeded"
                    }
                )
                
                document_perf_logger.stop_timer(timer_id, {
                    "document_id": document.id,
                    "status": "partially_processed",
                    "reason": "timeout"
                })
                
                logger.warning(f"Document processing timeout: {document.id} - stopped after {elapsed_time:.2f}s")
                return
            
            # Combine metadata and structure
            combined_metadata = {
                **metadata,
                "structure_info": document_structure
            }
            
            # Create full analysis results
            full_analysis = {
                "metadata": combined_metadata,
                "processing_time_seconds": round(time.time() - start_time, 2)
            }
            
            # Convert any NumPy types to Python native types for JSON serialization
            serializable_analysis = convert_numpy_to_python(full_analysis)
            
            # Update document with analysis results
            document.ai_analysis = json.dumps(serializable_analysis)
            document.status = "processed"
            
            # Log activity
            log_activity(
                db=db,
                action="document_processed",
                user_id=document.user_id,
                description=f"Document processed: {document.title}",
                ip_address=client_ip,
                details={
                    "document_id": document.id,
                    "processing_time": round(time.time() - start_time, 2)
                }
            )
            
            db.commit()
            
            document_perf_logger.stop_timer(timer_id, {
                "document_id": document.id,
                "status": "processed",
                "processing_time": round(time.time() - start_time, 2)
            })
            
            logger.info(f"Document processing completed: {document.id} with status {document.status}")
        
        except Exception as e:
            logger.error(f"Error in document content processing: {e}")
            document.status = "error"
            db.commit()
            
            # Log activity - ensure error details are JSON serializable
            error_details = convert_numpy_to_python({
                "document_id": document.id,
                "error": str(e)
            })
            
            log_activity(
                db=db,
                action="document_processing_error",
                user_id=document.user_id,
                description=f"Error processing document: {document.title}",
                ip_address=client_ip,
                details=error_details
            )
            
            document_perf_logger.log_operation_failed("process_document_content", e, 
                                                   details={"document_id": document.id})
    
    @staticmethod
    def generate_document(
        db: Session,
        user_id: int,
        template_type: str,
        input_data: Dict[str, Any],
        title: Optional[str] = None,
        description: Optional[str] = None,
        content: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> Tuple[Document, str]:
        """Generate a new document record from input content

        Args:
            db: Database session
            user_id: ID of the user generating the document
            template_type: Type of document to generate
            input_data: Input data for the document (metadata)
            title: Document title (optional)
            description: Document description (optional)
            content: Document content (optional)
            client_ip: Client IP address for activity logging

        Returns:
            Tuple[Document, str]: The document record and its content

        Raises:
            HTTPException: If document generation fails
        """
        timer_id = document_perf_logger.start_timer("generate_document", {
            "user_id": user_id,
            "template_type": template_type
        })
        
        try:
            # Generate default title if not provided
            if not title:
                title = f"{template_type.replace('_', ' ').title()} - {time.strftime('%Y-%m-%d')}"
            
            # Use provided content or generate a more substantial default content
            if content:
                generated_text = content
            else:
                # Create a more meaningful default content
                generated_text = f"""# {title or template_type.replace('_', ' ').title()} Document
                
## Summary
This is a {template_type.replace('_', ' ')} document generated on {time.strftime('%Y-%m-%d')}.

## Details
{json.dumps(input_data, indent=2)}

## Additional Information
Document created automatically by the system.
"""
            start_time = time.time()
            
            # Create document record with JSON-serializable analysis
            analysis_data = convert_numpy_to_python({
                "generated": True,
                "template_type": template_type,
                "input_data": input_data,
                "generation_time_seconds": round(time.time() - start_time, 2)
            })
            
            document = Document(
                user_id=user_id,
                title=title,
                description=description or f"{template_type} document",
                doc_type=template_type.replace("_", "-"),
                status="processed",
                file_content=generated_text,
                ai_analysis=json.dumps(analysis_data)
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Log activity
            log_activity(
                db=db,
                action="document_generated",
                user_id=user_id,
                description=f"Document generated: {title}",
                ip_address=client_ip,
                details={
                    "document_id": document.id,
                    "template_type": template_type,
                    "generation_time": round(time.time() - start_time, 2)
                }
            )
            
            document_perf_logger.stop_timer(timer_id, {
                "document_id": document.id,
                "processing_time": round(time.time() - start_time, 2)
            })
            
            logger.info(f"Document generated: {document.id}")
            return document, generated_text
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error generating document: {e}")
            document_perf_logger.log_operation_failed("generate_document", e)
            raise HTTPException(status_code=500, detail=f"Error generating document: {str(e)}")
    
    @staticmethod
    def get_user_documents(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Document]:
        """Get documents for a specific user

        Args:
            db: Database session
            user_id: ID of the user to get documents for
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List[Document]: List of document records
        """
        return db.query(Document).filter(Document.user_id == user_id).order_by(
            Document.created_at.desc()
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_document_by_id(db: Session, document_id: int, user_id: int = None) -> Document:
        """Get a document by ID

        Args:
            db: Database session
            document_id: ID of the document to get
            user_id: Optional user ID to verify ownership

        Returns:
            Document: The document record

        Raises:
            HTTPException: If document is not found or user is not authorized
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            logger.warning(f"Document not found: {document_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        if user_id is not None and document.user_id != user_id:
            logger.warning(f"User {user_id} attempted to access document {document_id} owned by user {document.user_id}")
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
        
        return document
    
    @staticmethod
    def delete_document(db: Session, document_id: int, user_id: int, client_ip: Optional[str] = None) -> None:
        """Delete a document

        Args:
            db: Database session
            document_id: ID of the document to delete
            user_id: ID of the user deleting the document
            client_ip: Client IP address for activity logging

        Raises:
            HTTPException: If document is not found or user is not authorized
        """
        document = DocumentService.get_document_by_id(db, document_id, user_id)
        
        # Remove the file if it exists
        if document.file_path and os.path.exists(document.file_path):
            try:
                os.remove(document.file_path)
            except Exception as e:
                logger.error(f"Error removing document file: {e}")
        
        # Log activity before deletion
        log_activity(
            db=db,
            action="document_deleted",
            user_id=user_id,
            description=f"Document deleted: {document.title}",
            ip_address=client_ip,
            details={
                "document_id": document_id,
                "document_title": document.title
            }
        )
        
        # Delete the document
        db.delete(document)
        db.commit()
        
        logger.info(f"Document deleted: {document_id}")

    @staticmethod
    def transform_document_with_templates(
        db: Session,
        document: Document,
        template_input: Document,
        template_output: Document,
        user_id: int
    ) -> Dict[str, Any]:
        """Transform a document using input/output template examples with timeout handling
        
        Args:
            db: Database session
            document: Document to transform
            template_input: Template document representing the input format
            template_output: Template document representing the desired output format
            user_id: ID of the user performing the transformation
            
        Returns:
            Dict[str, Any]: Transformation results including processed output
            
        Note:
            This implementation uses OpenAI to transform the document based on 
            the provided templates.
        """
        # Start performance timer
        timer_id = document_perf_logger.start_timer("transform_document_with_templates", {
            "document_id": document.id,
            "template_input_id": template_input.id,
            "template_output_id": template_output.id
        })
        
        start_time = time.time()
        
        try:
            # Get document content
            document_content = document.file_content or ""
            
            # Get template content
            template_input_content = template_input.file_content or ""
            template_output_content = template_output.file_content or ""
            
            # Extract file extensions for format detection
            document_ext = os.path.splitext(document.original_filename)[-1].lower() if document.original_filename else ".txt"
            template_input_ext = os.path.splitext(template_input.original_filename)[-1].lower() if template_input.original_filename else ".txt"
            template_output_ext = os.path.splitext(template_output.original_filename)[-1].lower() if template_output.original_filename else ".txt"
            
            # Log transformation request
            logger.info(
                f"Starting document transformation: document={document.id} ({document_ext}), "
                f"input_template={template_input.id} ({template_input_ext}), "
                f"output_template={template_output.id} ({template_output_ext})"
            )
            
            # First check processing time to ensure we have enough time
            # If we're already close to the timeout, return a special response
            elapsed_time = time.time() - start_time
            # For repo documents (depositions), we want to allow more processing time
            # For other document types, check if we've used 20% of our time just preparing
            if document.doc_type != "repo" and elapsed_time > MAX_PROCESSING_TIME * 0.2:
                document_perf_logger.log_threshold_exceeded(
                    "transform_document_preparation", 
                    MAX_PROCESSING_TIME * 0.2,
                    {"document_id": document.id, "elapsed_time": elapsed_time}
                )
                
                # Create a result indicating we need to retry with async processing
                result = {
                    "status": "retry_required",
                    "document_id": document.id,
                    "document_title": document.title,
                    "message": "Document is too complex for synchronous processing. Try with a smaller document or contact support.",
                    "error": "Processing time limit exceeded during preparation",
                    "timestamp": datetime.now().isoformat(),
                }
                
                document_perf_logger.stop_timer(timer_id, {
                    "status": "retry_required",
                    "processing_time": elapsed_time
                })
                
                return result
            
            # Call OpenAI service to transform the document - this is the most time consuming part
            try:
                openai_timer_id = document_perf_logger.start_timer("openai_transform", {
                    "document_id": document.id,
                    "input_size": len(document_content),
                    "input_template_size": len(template_input_content),
                    "output_template_size": len(template_output_content)
                })
                
                # Start a watchdog timer to prevent exceeding Heroku's 30s timeout
                # Note: This doesn't actually stop the API call, but helps us detect if we're approaching the limit
                timeout_reached = False
                api_start_time = time.time()
                
                # This is a synchronous API call - we need to carefully monitor time
                transformation_result = openai_service.transform_document(
                    document_content=document_content,
                    template_input_content=template_input_content,
                    template_output_content=template_output_content,
                    document_format=document_ext,
                    template_input_format=template_input_ext,
                    template_output_format=template_output_ext,
                    document_title=document.title,
                    template_input_title=template_input.title,
                    template_output_title=template_output.title,
                    document_type=document.doc_type
                )
                
                api_processing_time = time.time() - api_start_time
                document_perf_logger.stop_timer(openai_timer_id, {
                    "api_processing_time": api_processing_time
                })
                
                logger.info(f"OpenAI transformation completed in {api_processing_time:.2f} seconds")
                
                # Check if we've exceeded our processing time budget during API call
                elapsed_time = time.time() - start_time
                # For repo documents (depositions), allow more time before considering timeout
                if (document.doc_type == "repo" and elapsed_time > MAX_PROCESSING_TIME * 2) or \
                   (document.doc_type != "repo" and elapsed_time > MAX_PROCESSING_TIME):
                    document_perf_logger.log_threshold_exceeded("transform_document_with_templates", 
                                                          MAX_PROCESSING_TIME,
                                                          {"document_id": document.id,
                                                           "elapsed_time": elapsed_time})
                    # For repo documents, we still want to continue even if timeout is reached
                    timeout_reached = document.doc_type != "repo"
                
                # Extract information from the transformation result
                if isinstance(transformation_result, dict):
                    file_type = transformation_result.get("file_type", template_output_ext.lstrip("."))
                    transformed_content = transformation_result.get("content", "No content provided")
                    truncation_info = transformation_result.get("truncation_info", {})
                    parse_error = transformation_result.get("parse_error", None)
                else:
                    # Fallback if the result isn't a dict for some reason
                    file_type = template_output_ext.lstrip(".")
                    transformed_content = str(transformation_result)
                    truncation_info = {}
                    parse_error = "Unexpected response format"
                
                logger.info(f"Transformation resulted in file type: {file_type}")
                
                # If timeout was reached, we'll still try to save what we have
                if timeout_reached:
                    # Add a note about the timeout
                    if isinstance(transformation_result, dict):
                        transformation_result["timeout_warning"] = "The processing exceeded the time limit. Results may be incomplete."
                    transformed_content += "\n\n[WARNING: This transformation exceeded the processing time limit. Results may be incomplete.]"
                
                # Save the transformed content as a file with the appropriate extension
                try:
                    transformed_file_path = document_processor.save_transformed_file(
                        file_content=transformed_content,
                        file_type=file_type,
                        original_document_title=document.title,
                        user_id=user_id
                    )
                    logger.info(f"Saved transformed document to: {transformed_file_path}")
                except Exception as save_error:
                    logger.error(f"Error saving transformed file: {save_error}")
                    transformed_file_path = None
                
            except ValueError as ve:
                # If OpenAI API key is missing or there's a problem with the API
                logger.warning(f"OpenAI service error: {str(ve)}")
                
                # Return a fallback message if OpenAI transformation fails
                file_type = "txt"
                transformed_content = (
                    f"API transformation error: {str(ve)}\n\n"
                    f"Input Document: {document.title}\n"
                    f"Input Template: {template_input.title}\n"
                    f"Output Template: {template_output.title}\n\n"
                    f"Please check that your OpenAI API key is properly configured."
                )
                truncation_info = {}
                parse_error = str(ve)
            
            # Create a result object
            result = {
                "status": "success",
                "document_id": document.id,
                "document_title": document.title,
                "template_input_id": template_input.id,
                "template_input_title": template_input.title,
                "template_output_id": template_output.id,
                "template_output_title": template_output.title,
                "transformed_content": transformed_content,
                "timestamp": datetime.now().isoformat(),
                "formats": {
                    "document": document_ext,
                    "template_input": template_input_ext,
                    "template_output": template_output_ext,
                    "output": f".{file_type}" if not file_type.startswith(".") else file_type,
                },
                "file_type": file_type,
                "message": "Document transformation completed",
                "truncation_info": truncation_info
            }
            
            # Add file path if the file was saved successfully
            if 'transformed_file_path' in locals() and transformed_file_path:
                # Get relative path for display (removes the full server path)
                rel_path = os.path.relpath(transformed_file_path, start=os.getcwd())
                result["transformed_file_path"] = transformed_file_path
                result["transformed_file_name"] = os.path.basename(transformed_file_path)
                
                # Generate a signed URL for secure download (valid for 1 hour)
                import hashlib
                import hmac
                from app.services.auth_service import SECRET_KEY
                
                filename = os.path.basename(transformed_file_path)
                expires = int((datetime.now() + timedelta(hours=1)).timestamp())
                signature = hmac.new(
                    SECRET_KEY.encode(), 
                    f"{filename}:{user_id}:{expires}".encode(),
                    hashlib.sha256
                ).hexdigest()
                
                # Create a signed URL with auth params in the query string
                # This works for both local and S3 storage since our download route handles both
                result["download_path"] = f"/documents/downloads/{filename}?token={signature}&expires={expires}&user_id={user_id}"
            
            # Add any parse errors if they occurred
            if 'parse_error' in locals() and parse_error:
                result["parse_error"] = parse_error
            
            # Add timeout warning if needed
            if 'timeout_reached' in locals() and timeout_reached:
                result["timeout_warning"] = "Transformation exceeded the processing time limit. Results may be incomplete."
            
            # Log the transformation action
            log_activity(
                db=db,
                action="document_transformed",
                user_id=user_id,
                description=f"Document transformed: {document.title} using templates {template_input.title} and {template_output.title}",
                details={
                    "document_id": document.id,
                    "template_input_id": template_input.id,
                    "template_output_id": template_output.id,
                    "document_format": document_ext,
                    "template_input_format": template_input_ext,
                    "template_output_format": template_output_ext,
                    "transformation_time_seconds": time.time() - start_time if 'start_time' in locals() else None
                }
            )
            
            final_time = time.time() - start_time
            document_perf_logger.stop_timer(timer_id, {
                "document_id": document.id,
                "status": "success" if not ('timeout_reached' in locals() and timeout_reached) else "timeout_warning",
                "processing_time": final_time
            })
            
            logger.info(f"Document transformation completed for document {document.id} in {final_time:.2f}s")
            return result
            
        except Exception as e:
            final_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"Error transforming document: {e}")
            document_perf_logger.log_operation_failed("transform_document_with_templates", e, 
                                                   elapsed_seconds=final_time, 
                                                   details={"document_id": document.id})
            raise HTTPException(status_code=500, detail=f"Error transforming document: {str(e)}")

# Create a singleton instance
document_service = DocumentService()