import requests
import os
import json
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# File paths
DOCUMENT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/20250505_122441_Alexander_Sandy_Baptist_040325_MINI_PDFA.pdf"
TEMPLATE_INPUT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/input_depo.pdf"
TEMPLATE_OUTPUT_PATH = "/Users/Mike/Desktop/upwork/3_current_projects/rapidoc_021891240361152688586/tests/sample_docs/output_depo.csv"

def verify_file(file_path):
    """Verify file exists and is readable"""
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return False
    
    if not os.path.isfile(file_path):
        logger.error(f"Path is not a file: {file_path}")
        return False
    
    if not os.access(file_path, os.R_OK):
        logger.error(f"File is not readable: {file_path}")
        return False
    
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        logger.error(f"File is empty: {file_path}")
        return False
    
    logger.info(f"File verified: {file_path}, size: {file_size} bytes")
    return True

def register_user():
    """Register a test user and return credentials"""
    username = f"testuser_{int(time.time())}"
    email = f"test_{int(time.time())}@example.com"
    password = "Password123"
    
    response = requests.post(
        "http://localhost:8000/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password
        }
    )
    
    if response.status_code != 201:
        logger.error(f"Failed to register user: {response.text}")
        return None
    
    logger.info(f"User registered: {username}")
    return {"username": username, "password": password}

def login(username, password):
    """Login and get access token"""
    response = requests.post(
        "http://localhost:8000/auth/login",
        data={
            "username": username,
            "password": password
        }
    )
    
    if response.status_code != 200:
        logger.error(f"Failed to login: {response.text}")
        return None
    
    token = response.json().get("access_token")
    logger.info("Login successful, got access token")
    return token

def upload_file(token, file_path, title, description, doc_type, tag=None):
    """Upload a file and return document ID"""
    # Verify file first
    if not verify_file(file_path):
        return None
    
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, "rb") as file:
        file_content = file.read()
        logger.info(f"Read file content: {len(file_content)} bytes")
        
        files = {"file": (os.path.basename(file_path), file_content)}
        data = {
            "title": title,
            "description": description,
            "doc_type": doc_type
        }
        
        if tag:
            data["tag"] = tag
        
        response = requests.post(
            "http://localhost:8000/documents/upload",
            headers=headers,
            files=files,
            data=data
        )
    
    if response.status_code != 201:
        logger.error(f"Failed to upload file: {response.text}")
        return None
    
    doc_id = response.json().get("id")
    logger.info(f"Document uploaded, ID: {doc_id}")
    return doc_id

def main():
    """Main function"""
    # Verify all files first
    for file_path in [DOCUMENT_PATH, TEMPLATE_INPUT_PATH, TEMPLATE_OUTPUT_PATH]:
        if not verify_file(file_path):
            return
    
    # Register user
    user = register_user()
    if not user:
        return
    
    # Login
    token = login(user["username"], user["password"])
    if not token:
        return
    
    # Upload main document
    logger.info(f"Uploading main document: {DOCUMENT_PATH}")
    doc_id = upload_file(
        token,
        DOCUMENT_PATH,
        "Test Document",
        "Document for transformation",
        "other"
    )
    if not doc_id:
        return
    
    # Upload input template
    logger.info(f"Uploading input template: {TEMPLATE_INPUT_PATH}")
    template_input_id = upload_file(
        token,
        TEMPLATE_INPUT_PATH,
        "Input Template",
        "Input format template",
        "other",
        tag="template"
    )
    if not template_input_id:
        return
    
    # Upload output template
    logger.info(f"Uploading output template: {TEMPLATE_OUTPUT_PATH}")
    template_output_id = upload_file(
        token,
        TEMPLATE_OUTPUT_PATH,
        "Output Template",
        "Output format template",
        "other",
        tag="template"
    )
    if not template_output_id:
        return
    
    # Wait for processing
    logger.info("Waiting for processing to complete...")
    time.sleep(10)
    
    # Transform document
    logger.info(f"Transforming document {doc_id} with templates {template_input_id} and {template_output_id}")
    response = requests.post(
        f"http://localhost:8000/documents/{doc_id}/transform-with-templates",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "template_input_id": template_input_id,
            "template_output_id": template_output_id
        }
    )
    
    # Process response
    if response.status_code in [200, 422]:
        result = response.json()
        
        if response.status_code == 200:
            logger.info("Transformation successful")
            if "transformed_content" in result:
                preview = result["transformed_content"][:200] + "..." if len(result["transformed_content"]) > 200 else result["transformed_content"]
                logger.info(f"Preview: {preview}")
                
            if "download_path" in result:
                logger.info(f"Download path: {result['download_path']}")
        
        elif response.status_code == 422:
            logger.info(f"Transformation timeout/retry required: {result}")
    
    else:
        logger.error(f"Transformation failed: {response.status_code} - {response.text}")

if __name__ == "__main__":
    main()