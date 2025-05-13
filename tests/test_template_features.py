import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
import csv
import pandas as pd
import io

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/template_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
ACCESS_TOKEN = None
TEST_USER = {
    'email': f'temptest_{int(time.time())}@example.com',
    'username': f'temptest_{int(time.time())}',
    'password': 'TestPassword123'
}

# Test file paths
SAMPLE_DOCS_DIR = "tests/sample_docs"
TEMPLATE_DOCS_DIR = os.path.join(SAMPLE_DOCS_DIR, "templates")
os.makedirs(SAMPLE_DOCS_DIR, exist_ok=True)
os.makedirs(TEMPLATE_DOCS_DIR, exist_ok=True)

def create_sample_files():
    """Create sample files for testing template uploads"""
    sample_files = {}
    
    try:
        # Create sample CSV file
        csv_path = os.path.join(TEMPLATE_DOCS_DIR, "template_data.csv")
        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['id', 'name', 'value', 'category'])
            writer.writerow(['1', 'Template A', '100.50', 'Standard'])
            writer.writerow(['2', 'Template B', '200.75', 'Premium'])
            writer.writerow(['3', 'Template C', '150.25', 'Standard'])
            writer.writerow(['4', 'Template D', '300.00', 'Premium'])
            writer.writerow(['5', 'Template E', '125.75', 'Standard'])
        sample_files['csv'] = csv_path
        logger.info(f"Created sample CSV file at {csv_path}")
        
        # Create sample TXT file
        txt_path = os.path.join(TEMPLATE_DOCS_DIR, "template_content.txt")
        with open(txt_path, 'w') as txtfile:
            txtfile.write("This is a template document content.\n\n")
            txtfile.write("Section 1: Introduction\n")
            txtfile.write("This template can be used for document analysis.\n\n")
            txtfile.write("Section 2: Terms\n")
            txtfile.write("The following terms apply to all documents created from this template.\n\n")
            txtfile.write("Section 3: Conclusion\n")
            txtfile.write("This concludes the template content.")
        sample_files['txt'] = txt_path
        logger.info(f"Created sample TXT file at {txt_path}")
        
        # Create sample JSON file
        json_path = os.path.join(TEMPLATE_DOCS_DIR, "template_config.json")
        config_data = {
            "template_name": "Standard Contract",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "sections": [
                {"id": 1, "name": "Introduction", "required": True},
                {"id": 2, "name": "Parties", "required": True},
                {"id": 3, "name": "Terms", "required": True},
                {"id": 4, "name": "Signatures", "required": True},
                {"id": 5, "name": "Appendices", "required": False}
            ],
            "variables": {
                "party_a": {"type": "string", "required": True},
                "party_b": {"type": "string", "required": True},
                "agreement_date": {"type": "date", "required": True},
                "amount": {"type": "number", "required": True},
                "term_months": {"type": "integer", "required": True}
            }
        }
        with open(json_path, 'w') as jsonfile:
            json.dump(config_data, jsonfile, indent=2)
        sample_files['json'] = json_path
        logger.info(f"Created sample JSON file at {json_path}")
        
        # Create sample Excel file if pandas and openpyxl are available
        try:
            excel_path = os.path.join(TEMPLATE_DOCS_DIR, "template_data.xlsx")
            
            # Create a pandas DataFrame
            df1 = pd.DataFrame({
                'id': [1, 2, 3, 4, 5],
                'name': ['Item A', 'Item B', 'Item C', 'Item D', 'Item E'],
                'value': [100.50, 200.75, 150.25, 300.00, 125.75],
                'category': ['Standard', 'Premium', 'Standard', 'Premium', 'Standard']
            })
            
            df2 = pd.DataFrame({
                'variable': ['party_a', 'party_b', 'agreement_date', 'amount', 'term_months'],
                'type': ['string', 'string', 'date', 'number', 'integer'],
                'required': [True, True, True, True, True],
                'description': [
                    'First party name', 
                    'Second party name',
                    'Date of agreement',
                    'Contract amount',
                    'Term length in months'
                ]
            })
            
            # Create an Excel writer
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df1.to_excel(writer, sheet_name='Data', index=False)
                df2.to_excel(writer, sheet_name='Variables', index=False)
            
            sample_files['xlsx'] = excel_path
            logger.info(f"Created sample Excel file at {excel_path}")
        except Exception as e:
            logger.warning(f"Could not create Excel test file: {e}")
        
        return sample_files
    
    except Exception as e:
        logger.error(f"Failed to create sample files: {e}")
        return {}

def register_and_login():
    """Register a new user and get access token"""
    global ACCESS_TOKEN
    
    try:
        # Register new user
        response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        if response.status_code != 201:
            logger.error(f"Registration failed: {response.text}")
            return False
        
        logger.info(f"Registered test user: {TEST_USER['username']}")
        
        # Login
        login_data = {
            'username': TEST_USER['username'],
            'password': TEST_USER['password']
        }
        response = requests.post(
            f"{BASE_URL}/auth/login", 
            data=login_data
        )
        
        if response.status_code != 200:
            logger.error(f"Login failed: {response.text}")
            return False
        
        token_data = response.json()
        ACCESS_TOKEN = token_data["access_token"]
        logger.info(f"Logged in successfully, received access token")
        return True
    
    except Exception as e:
        logger.error(f"Error in registration/login: {e}")
        return False

def upload_template_file(file_path, title, description):
    """Upload a file as a template"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return None
    
    try:
        # Upload file with template tag
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'title': title,
                'description': description,
                'doc_type': 'repo',
                'tag': 'template'  # This marks it as a template
            }
            headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
            
            response = requests.post(
                f"{BASE_URL}/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code != 201:
            logger.error(f"Template upload failed: {response.text}")
            return None
        
        document_data = response.json()
        document_id = document_data['id']
        logger.info(f"Uploaded template document with ID: {document_id}")
        
        # Wait for processing to complete
        logger.info("Waiting for template processing to complete...")
        time.sleep(3)  # Wait for processing
        
        return document_id
    
    except Exception as e:
        logger.error(f"Error in template upload: {e}")
        return None

def test_regular_document_upload(file_path, title, description):
    """Upload a file as a regular document (not a template)"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return None
    
    try:
        # Upload file without template tag
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {
                'title': title,
                'description': description,
                'doc_type': 'repo'
                # No tag means it's a regular document
            }
            headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
            
            response = requests.post(
                f"{BASE_URL}/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code != 201:
            logger.error(f"Regular document upload failed: {response.text}")
            return None
        
        document_data = response.json()
        document_id = document_data['id']
        logger.info(f"Uploaded regular document with ID: {document_id}")
        
        # Wait for processing to complete
        logger.info("Waiting for document processing to complete...")
        time.sleep(3)  # Wait for processing
        
        return document_id
    
    except Exception as e:
        logger.error(f"Error in regular document upload: {e}")
        return None

def test_get_templates():
    """Test retrieving all template documents"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return False
    
    try:
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        
        # Get only template documents 
        response = requests.get(
            f"{BASE_URL}/documents/?tag=template",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to retrieve templates: {response.text}")
            return False
        
        templates = response.json()
        logger.info(f"Retrieved {len(templates)} template documents")
        
        # Verify all retrieved documents have the template tag
        template_count = 0
        for doc in templates:
            if doc.get('tag') == 'template':
                template_count += 1
        
        if template_count == len(templates) and template_count > 0:
            logger.info("All retrieved documents have the template tag")
            return True
        else:
            logger.warning(f"Expected all documents to have template tag, but found {template_count} out of {len(templates)}")
            return False
    
    except Exception as e:
        logger.error(f"Error in template retrieval test: {e}")
        return False

def test_get_regular_documents():
    """Test retrieving regular (non-template) documents"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return False
    
    try:
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        
        # Get regular documents (exclude templates)
        response = requests.get(
            f"{BASE_URL}/documents/?include_templates=false",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to retrieve regular documents: {response.text}")
            return False
        
        documents = response.json()
        logger.info(f"Retrieved {len(documents)} regular documents")
        
        # Verify none of the retrieved documents have the template tag
        non_template_count = 0
        for doc in documents:
            if doc.get('tag') != 'template':
                non_template_count += 1
        
        if non_template_count == len(documents) and non_template_count > 0:
            logger.info("All retrieved documents are regular (non-template) documents")
            return True
        else:
            logger.warning(f"Expected 0 templates, but found {len(documents) - non_template_count} templates out of {len(documents)} documents")
            return False
    
    except Exception as e:
        logger.error(f"Error in regular document retrieval test: {e}")
        return False

def test_template_analysis(template_id):
    """Test retrieving and analyzing a template document"""
    if not ACCESS_TOKEN or not template_id:
        logger.error("No access token or template ID available")
        return False
    
    try:
        headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
        
        # Get document details
        response = requests.get(
            f"{BASE_URL}/documents/{template_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get template details: {response.text}")
            return False
        
        template = response.json()
        logger.info(f"Retrieved template details for ID {template_id}, status: {template['status']}")
        
        # Verify it has the template tag
        if template.get('tag') != 'template':
            logger.error(f"Document {template_id} is not a template! Tag = {template.get('tag')}")
            return False
        
        # Get template analysis
        response = requests.get(
            f"{BASE_URL}/documents/{template_id}/analysis",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get template analysis: {response.text}")
            return False
        
        analysis = response.json()
        logger.info(f"Retrieved template analysis with {len(json.dumps(analysis))} characters")
        
        # Check for expected analysis fields 
        if 'metadata' in analysis:
            logger.info(f"Template analysis structure looks correct for {template['title']}")
            return True
        else:
            logger.warning("Template analysis structure is missing expected fields")
            return False
    
    except Exception as e:
        logger.error(f"Error in template analysis test: {e}")
        return False

def run_tests():
    """Run all template feature tests"""
    try:
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        logger.info("Starting template feature tests")
        
        # Check if server is running
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                logger.error(f"Server health check failed: {response.status_code}")
                return False
            logger.info("Server is running")
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to server. Make sure it's running.")
            return False
        
        # Register and login
        if not register_and_login():
            logger.error("Registration/login test failed")
            return False
        logger.info("Registration and login successful")
        
        # Create sample files
        sample_files = create_sample_files()
        if not sample_files:
            logger.error("Failed to create sample files")
            return False
        logger.info(f"Created {len(sample_files)} sample files for testing")
        
        # Upload each file type as a template
        template_ids = []
        for file_type, file_path in sample_files.items():
            template_id = upload_template_file(
                file_path, 
                f"Template {file_type.upper()}", 
                f"Sample {file_type.upper()} template file"
            )
            if template_id:
                template_ids.append(template_id)
                logger.info(f"Successfully uploaded {file_type} template with ID {template_id}")
            else:
                logger.warning(f"Failed to upload {file_type} template")
        
        if not template_ids:
            logger.error("All template uploads failed")
            return False
        
        # Upload one file as a regular document for comparison
        regular_doc_id = test_regular_document_upload(
            list(sample_files.values())[0], 
            "Regular Document", 
            "Sample non-template document"
        )
        
        if not regular_doc_id:
            logger.warning("Regular document upload failed, but continuing tests")
        
        # Test retrieving templates
        if not test_get_templates():
            logger.error("Template retrieval test failed")
            return False
        logger.info("Template retrieval test passed")
        
        # Test retrieving regular documents
        if not test_get_regular_documents():
            logger.error("Regular document retrieval test failed")
            return False
        logger.info("Regular document retrieval test passed")
        
        # Test template analysis for each uploaded template
        analysis_success = False
        for template_id in template_ids:
            if test_template_analysis(template_id):
                analysis_success = True
                logger.info(f"Template analysis test passed for template ID {template_id}")
                break
            else:
                logger.warning(f"Template analysis test failed for template ID {template_id}")
        
        if not analysis_success and template_ids:
            logger.error("All template analysis tests failed")
            return False
        
        logger.info("All template feature tests completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"An unexpected error occurred during testing: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)