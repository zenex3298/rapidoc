import os
import sys
import json
import time
import logging
from app.services.document_service import document_service
from app.models.document import Document
from app.core.database import SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths
DOCUMENT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/20250505_122441_Alexander_Sandy_Baptist_040325_MINI_PDFA.pdf"
TEMPLATE_INPUT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/input_depo.pdf"
TEMPLATE_OUTPUT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/output_depo.csv"

def get_db():
    """Get a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_test_document(db: Session, file_path: str, title: str, tag: str = None) -> Document:
    """Create a test document directly in the database"""
    try:
        # Create document record
        document = Document(
            user_id=1,  # Assuming admin user has ID 1
            title=title,
            description=f"Test document from {os.path.basename(file_path)}",
            doc_type="other",
            status="processed",  # Skip the processing step
            original_filename=os.path.basename(file_path),
            file_path=file_path,
            tag=tag
        )
        
        # Read file content
        with open(file_path, 'rb') as f:
            content = f.read()
            document.file_content = content.decode('utf-8', errors='ignore')
        
        # Add to database
        db.add(document)
        db.commit()
        db.refresh(document)
        
        logger.info(f"Created test document: {document.id} - {document.title}")
        return document
    
    except Exception as e:
        logger.error(f"Error creating test document: {e}")
        db.rollback()
        return None

def test_transform_documents():
    """Test document transformation directly using the service"""
    try:
        # Get database session
        db = next(get_db())
        
        # Create test documents
        logger.info("Creating test documents...")
        document = create_test_document(db, DOCUMENT_PATH, "Test Document")
        if not document:
            return False
        
        template_input = create_test_document(db, TEMPLATE_INPUT_PATH, "Input Template", tag="template")
        if not template_input:
            return False
        
        template_output = create_test_document(db, TEMPLATE_OUTPUT_PATH, "Output Template", tag="template")
        if not template_output:
            return False
        
        # Call the transform method directly
        logger.info(f"Transforming document {document.id} using templates {template_input.id} and {template_output.id}...")
        
        try:
            result = document_service.transform_document_with_templates(
                db=db,
                document=document,
                template_input=template_input,
                template_output=template_output,
                user_id=1  # Assuming admin user has ID 1
            )
            
            logger.info("Transformation successful!")
            logger.info(f"Result status: {result.get('status', 'unknown')}")
            
            if "transformed_content" in result:
                content_preview = result["transformed_content"][:200]
                logger.info(f"Content preview: {content_preview}...")
            
            if "download_path" in result:
                logger.info(f"Download path: {result['download_path']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during transformation: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_transform_documents()
    if not success:
        sys.exit(1)
    sys.exit(0)