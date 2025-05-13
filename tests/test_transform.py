import requests
import json
import os
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL and auth
BASE_URL = "http://localhost:8000"
TEST_USER = {
    'email': f'test_{int(time.time())}@example.com',
    'username': f'testuser_{int(time.time())}',
    'password': 'TestPassword123'
}

# Document file paths
DOCUMENT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/20250505_122441_Alexander_Sandy_Baptist_040325_MINI_PDFA.pdf"
TEMPLATE_INPUT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/input_depo.pdf"
TEMPLATE_OUTPUT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/output_depo.csv"

def register_user():
    """Register a test user"""
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        if response.status_code != 201:
            logger.error(f"Registration failed: {response.text}")
            return False
        
        logger.info(f"Registered test user: {TEST_USER['username']}")
        return True
    
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        return False

def get_token():
    """Get authentication token"""
    try:
        login_data = {
            'username': TEST_USER['username'],
            'password': TEST_USER['password']
        }
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        
        if response.status_code != 200:
            logger.error(f"Login failed: {response.text}")
            return None
        
        token_data = response.json()
        logger.info("Login successful, received access token")
        return token_data["access_token"]
    
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return None

def upload_document(token, file_path, title, description, doc_type, tag=None):
    """Upload a document and return its ID"""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'title': title,
                'description': description,
                'doc_type': doc_type
            }
            if tag:
                data['tag'] = tag
                
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.post(
                f"{BASE_URL}/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code != 201:
            logger.error(f"Upload failed: {response.text}")
            return None
        
        document_data = response.json()
        logger.info(f"Successfully uploaded document with ID: {document_data['id']}")
        return document_data['id']
    
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return None

def transform_document(token, document_id, template_input_id, template_output_id):
    """Transform a document with the given templates"""
    try:
        headers = {'Authorization': f'Bearer {token}'}
        transform_data = {
            'template_input_id': template_input_id,
            'template_output_id': template_output_id
        }
        
        response = requests.post(
            f"{BASE_URL}/documents/{document_id}/transform-with-templates",
            json=transform_data,
            headers=headers
        )
        
        return response.status_code, response.json()
    
    except Exception as e:
        logger.error(f"Error transforming document: {e}")
        return None, None

def main():
    """Run the document transformation test"""
    logger.info("Starting document transformation test")
    
    # Step 1: Register user and get authentication token
    if not register_user():
        logger.error("Failed to register test user")
        return False
    
    token = get_token()
    if not token:
        logger.error("Failed to get authentication token")
        return False
    
    # Step 2: Upload all three documents
    logger.info(f"Uploading main document: {DOCUMENT_PATH}")
    document_id = upload_document(
        token=token,
        file_path=DOCUMENT_PATH,
        title="Deposition Document",
        description="Deposition document for transformation test",
        doc_type="other"
    )
    
    if not document_id:
        logger.error("Failed to upload main document")
        return False
    
    logger.info(f"Uploading input template: {TEMPLATE_INPUT_PATH}")
    template_input_id = upload_document(
        token=token,
        file_path=TEMPLATE_INPUT_PATH,
        title="Deposition Input Template",
        description="Template for input format",
        doc_type="other",
        tag="template"
    )
    
    if not template_input_id:
        logger.error("Failed to upload input template")
        return False
    
    logger.info(f"Uploading output template: {TEMPLATE_OUTPUT_PATH}")
    template_output_id = upload_document(
        token=token,
        file_path=TEMPLATE_OUTPUT_PATH,
        title="Deposition Output Template",
        description="Template for output format",
        doc_type="other",
        tag="template"
    )
    
    if not template_output_id:
        logger.error("Failed to upload output template")
        return False
    
    # Wait for processing to complete
    logger.info("Waiting for documents to be processed...")
    time.sleep(10)
    
    # Step 3: Transform the document
    logger.info(f"Transforming document {document_id} with templates {template_input_id} and {template_output_id}")
    status_code, result = transform_document(token, document_id, template_input_id, template_output_id)
    
    if not status_code:
        logger.error("Failed to transform document")
        return False
    
    logger.info(f"Transformation completed with status code {status_code}")
    
    if status_code == 200:
        logger.info("Transformation succeeded")
        if "transformed_content" in result:
            content_preview = result["transformed_content"][:200] + "..."
            logger.info(f"Content preview: {content_preview}")
        
        if "download_path" in result:
            logger.info(f"Download path: {result['download_path']}")
    
    elif status_code == 422:
        if "status" in result and result["status"] == "retry_required":
            logger.info("Document transformation timeout - requires asynchronous processing")
            logger.info(f"Message: {result.get('message', 'No message')}")
            logger.info(f"Detail: {result.get('detail', 'No details')}")
    
    else:
        logger.error(f"Unexpected status code: {status_code}")
        logger.error(f"Response: {json.dumps(result, indent=2)}")
        return False
    
    logger.info("Document transformation test completed successfully")
    return True

if __name__ == "__main__":
    main()