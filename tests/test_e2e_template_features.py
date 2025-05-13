import os
import sys
import json
import time
import logging
import requests
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/e2e_template_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER = {
    'email': f'e2etest_{int(time.time())}@example.com',
    'username': f'e2etest_{int(time.time())}',
    'password': 'TestPassword123'
}
ACCESS_TOKEN = None

# Test file paths
SAMPLE_DOCS_DIR = "tests/sample_docs"
TEMPLATE_DOCS_DIR = os.path.join(SAMPLE_DOCS_DIR, "templates")

class Browser:
    """Browser context manager for Selenium tests"""
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        
    def __enter__(self):
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(5)
        return self.driver
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()

def register_and_login_api():
    """Register and login via API to get an access token"""
    global ACCESS_TOKEN
    
    try:
        # Register new user
        logger.info(f"Registering test user: {TEST_USER['username']}")
        response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        if response.status_code != 201:
            logger.error(f"Registration failed: {response.text}")
            return False
        
        # Login
        logger.info(f"Logging in as test user: {TEST_USER['username']}")
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

def test_template_listing_page():
    """Test the template listing page functionality"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return False
    
    try:
        with Browser() as driver:
            # Navigate to login page
            driver.get(f"{BASE_URL}/login")
            
            # Wait for page to load and check title
            assert "Login - RapidocsAI" in driver.title
            
            # Save the token to localStorage before navigating to template page
            driver.execute_script(f"localStorage.setItem('auth_token', '{ACCESS_TOKEN}');")
            
            # Navigate to templates page
            driver.get(f"{BASE_URL}/templates")
            
            # Wait for templates page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            
            # Check page title and heading
            assert "Template Documents" in driver.title
            h1_element = driver.find_element(By.TAG_NAME, "h1")
            assert "Template Documents" in h1_element.text
            
            # Check for upload button
            upload_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Upload New Template')]")
            assert upload_btn.is_displayed()
            
            # Wait for table to load (either with templates or "No templates" message)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "templates-table-body"))
            )
            
            # Table content is loaded via JavaScript, give it time to load
            time.sleep(2)
            
            table_body = driver.find_element(By.ID, "templates-table-body")
            try:
                # Check if we have templates or the "no templates" message
                empty_message = table_body.find_element(By.XPATH, "//td[contains(text(), 'No template documents found')]")
                logger.info("No templates found message displayed correctly")
            except NoSuchElementException:
                # If we have templates, check that the table has rows
                rows = table_body.find_elements(By.TAG_NAME, "tr")
                logger.info(f"Found {len(rows)} template documents in the table")
            
            logger.info("Template listing page test passed")
            return True
    
    except Exception as e:
        logger.error(f"Error in template listing page test: {e}")
        return False
    
def test_template_upload_page(file_path, title, doc_type):
    """Test the template upload functionality"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return False
    
    try:
        with Browser() as driver:
            # Set auth token in localStorage
            driver.get(f"{BASE_URL}/login")
            driver.execute_script(f"localStorage.setItem('auth_token', '{ACCESS_TOKEN}');")
            
            # Navigate to template upload page
            driver.get(f"{BASE_URL}/template-upload")
            
            # Wait for upload page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "upload-form"))
            )
            
            # Check page title
            assert "Upload Template" in driver.title
            
            # Check form fields
            title_input = driver.find_element(By.ID, "title")
            description_input = driver.find_element(By.ID, "description")
            doc_type_select = driver.find_element(By.ID, "doc_type")
            file_input = driver.find_element(By.ID, "file")
            tag_input = driver.find_element(By.ID, "tag")
            upload_button = driver.find_element(By.ID, "upload-button")
            
            # Check tag field is hidden and set to "template"
            assert not tag_input.is_displayed()
            assert tag_input.get_attribute("value") == "template"
            
            # Fill form
            title_input.send_keys(title)
            description_input.send_keys(f"E2E test template upload - {datetime.now()}")
            driver.execute_script(f"document.getElementById('doc_type').value = '{doc_type}';")
            
            # Upload file
            file_input.send_keys(os.path.abspath(file_path))
            
            # Submit form
            upload_button.click()
            
            # Wait for upload success message
            try:
                success_element = WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.ID, "upload-success"))
                )
                logger.info(f"Successfully uploaded template: {title}")
                return True
            except TimeoutException:
                logger.error("Template upload timeout or error")
                # Check if there was an error message
                try:
                    error_container = driver.find_element(By.ID, "upload-error")
                    if error_container.is_displayed():
                        error_message = driver.find_element(By.ID, "error-message").text
                        logger.error(f"Upload error: {error_message}")
                except NoSuchElementException:
                    logger.error("Upload error: Could not find error message")
                return False
    
    except Exception as e:
        logger.error(f"Error in template upload test: {e}")
        return False

def test_view_template_details():
    """Test viewing template details"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return False
    
    try:
        # First upload a template via API to ensure we have at least one template
        csv_path = os.path.join(TEMPLATE_DOCS_DIR, "template_data.csv")
        if not os.path.exists(csv_path):
            logger.error(f"Test file not found: {csv_path}")
            return False
        
        with open(csv_path, 'rb') as f:
            files = {'file': f}
            data = {
                'title': f'API Template Upload {int(time.time())}',
                'description': 'Uploaded via API for E2E test',
                'doc_type': 'other',
                'tag': 'template'
            }
            headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
            
            response = requests.post(
                f"{BASE_URL}/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code != 201:
            logger.error(f"API upload failed: {response.text}")
            return False
        
        template_id = response.json()['id']
        logger.info(f"Uploaded template via API with ID: {template_id}")
        
        # Now test viewing template details in the UI
        with Browser() as driver:
            # Set auth token in localStorage
            driver.get(f"{BASE_URL}/login")
            driver.execute_script(f"localStorage.setItem('auth_token', '{ACCESS_TOKEN}');")
            
            # Navigate to templates page
            driver.get(f"{BASE_URL}/templates")
            
            # Wait for templates to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "templates-table-body"))
            )
            
            # Give time for JavaScript to populate the table
            time.sleep(2)
            
            # Click view button for our template
            # First find all view buttons
            view_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'View')]")
            if not view_buttons:
                logger.error("No View buttons found in template table")
                return False
            
            # Click the first view button
            view_buttons[0].click()
            
            # Wait for modal to appear
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "modal-content"))
            )
            
            # Check modal title and content
            modal_title = driver.find_element(By.CLASS_NAME, "modal-title")
            assert "Template:" in modal_title.text
            
            # Check modal contains expected fields
            modal_body = driver.find_element(By.CLASS_NAME, "modal-body")
            assert "Template ID:" in modal_body.text
            assert "Description:" in modal_body.text
            assert "Document Type:" in modal_body.text
            assert "Status:" in modal_body.text
            
            # Check for Analyze button
            analyze_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Analyze')]")
            assert analyze_button.is_displayed()
            
            logger.info("Template view details test passed")
            return True
    
    except Exception as e:
        logger.error(f"Error in view template details test: {e}")
        return False

def test_analyze_template():
    """Test template analysis functionality"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return False
    
    try:
        with Browser() as driver:
            # Set auth token in localStorage
            driver.get(f"{BASE_URL}/login")
            driver.execute_script(f"localStorage.setItem('auth_token', '{ACCESS_TOKEN}');")
            
            # Navigate to templates page
            driver.get(f"{BASE_URL}/templates")
            
            # Wait for templates to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "templates-table-body"))
            )
            
            # Give time for JavaScript to populate the table
            time.sleep(2)
            
            # Click view button for the first template
            view_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'View')]")
            if not view_buttons:
                logger.error("No View buttons found in template table")
                return False
            
            view_buttons[0].click()
            
            # Wait for modal to appear
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "modal-content"))
            )
            
            # Click analyze button
            analyze_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Analyze')]")
            analyze_button.click()
            
            # Wait for analysis modal to appear
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "analysisModal"))
            )
            
            # Check analysis tabs exist
            summary_tab = driver.find_element(By.ID, "summary-tab")
            metadata_tab = driver.find_element(By.ID, "metadata-tab")
            raw_tab = driver.find_element(By.ID, "raw-tab")
            
            assert summary_tab.is_displayed()
            assert metadata_tab.is_displayed()
            assert raw_tab.is_displayed()
            
            # Check summary tab content
            summary_pane = driver.find_element(By.ID, "summary")
            assert "Template Document" in summary_pane.text
            assert "Document Overview" in summary_pane.text
            
            # Check metadata tab
            metadata_tab.click()
            time.sleep(1)  # Allow tab to activate
            metadata_pane = driver.find_element(By.ID, "metadata")
            assert "Property" in metadata_pane.text
            assert "Value" in metadata_pane.text
            
            # Check raw JSON tab
            raw_tab.click()
            time.sleep(1)  # Allow tab to activate
            raw_pane = driver.find_element(By.ID, "raw")
            assert "{" in raw_pane.text  # Should contain JSON
            
            logger.info("Template analysis test passed")
            return True
    
    except Exception as e:
        logger.error(f"Error in template analysis test: {e}")
        return False

def test_filter_templates_api():
    """Test the template filtering API"""
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
            logger.error(f"Template retrieval API failed: {response.text}")
            return False
        
        templates = response.json()
        logger.info(f"Retrieved {len(templates)} template documents via API")
        
        # Verify all retrieved documents have the template tag
        template_count = sum(1 for doc in templates if doc.get('tag') == 'template')
        if template_count != len(templates):
            logger.error(f"Expected all documents to have template tag, but found {template_count} out of {len(templates)}")
            return False
        
        # Get regular documents (explicitly exclude templates)
        response = requests.get(
            f"{BASE_URL}/documents/?include_templates=false",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Regular document retrieval API failed: {response.text}")
            return False
        
        regular_docs = response.json()
        logger.info(f"Retrieved {len(regular_docs)} regular documents via API")
        
        # Verify none of the retrieved documents have the template tag
        non_template_count = sum(1 for doc in regular_docs if doc.get('tag') != 'template')
        if non_template_count != len(regular_docs):
            logger.error(f"Expected 0 templates in regular docs, but found {len(regular_docs) - non_template_count}")
            return False
        
        logger.info("Template filtering API test passed")
        return True
    
    except Exception as e:
        logger.error(f"Error in template filtering API test: {e}")
        return False

def test_delete_template():
    """Test template deletion functionality"""
    if not ACCESS_TOKEN:
        logger.error("No access token available")
        return False
    
    try:
        # First upload a template specifically for deletion
        csv_path = os.path.join(TEMPLATE_DOCS_DIR, "template_data.csv")
        if not os.path.exists(csv_path):
            logger.error(f"Test file not found: {csv_path}")
            return False
        
        with open(csv_path, 'rb') as f:
            files = {'file': f}
            data = {
                'title': f'Deletion Test Template {int(time.time())}',
                'description': 'Template to be deleted in E2E test',
                'doc_type': 'other',
                'tag': 'template'
            }
            headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
            
            response = requests.post(
                f"{BASE_URL}/documents/upload",
                files=files,
                data=data,
                headers=headers
            )
        
        if response.status_code != 201:
            logger.error(f"API upload for deletion test failed: {response.text}")
            return False
        
        template_id = response.json()['id']
        template_title = response.json()['title']
        logger.info(f"Uploaded template for deletion test with ID: {template_id}")
        
        # Now test deletion in the UI
        with Browser() as driver:
            # Set auth token in localStorage
            driver.get(f"{BASE_URL}/login")
            driver.execute_script(f"localStorage.setItem('auth_token', '{ACCESS_TOKEN}');")
            
            # Navigate to templates page
            driver.get(f"{BASE_URL}/templates")
            
            # Wait for templates to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "templates-table-body"))
            )
            
            # Give time for JavaScript to populate the table
            time.sleep(2)
            
            # Override alert handling to prevent issues with the confirmation alert
            # First set up the confirm override using JavaScript
            driver.execute_script("""
                window.originalConfirm = window.confirm;
                window.confirm = function() { return true; };
            """)
            
            # Handle alerts automatically
            driver.execute_script('window.alert = function() { return true; };')
            
            # Find and click delete button more safely
            rows = driver.find_elements(By.XPATH, "//tbody[@id='templates-table-body']/tr")
            delete_clicked = False
            
            for row in rows:
                try:
                    # Get the ID from the first column
                    id_cell = row.find_element(By.XPATH, "./td[1]")
                    if id_cell.text == str(template_id):
                        # Find and click the delete button
                        delete_btn = row.find_element(By.XPATH, ".//button[contains(@class, 'btn-danger')]")
                        delete_btn.click()
                        delete_clicked = True
                        logger.info(f"Delete button clicked for template {template_id}")
                        break
                except Exception as e:
                    logger.warning(f"Error finding row or button: {e}")
                    continue
            
            if not delete_clicked:
                logger.error(f"Could not find delete button for template {template_id}")
                
            # Wait a moment for the delete request to be processed
            time.sleep(3)
            
            # Verify template was deleted via API
            time.sleep(2)  # Give time for deletion to complete
            headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
            response = requests.get(
                f"{BASE_URL}/documents/{template_id}",
                headers=headers
            )
            
            if response.status_code == 404:
                logger.info(f"Template {template_id} was successfully deleted")
                return True
            else:
                logger.error(f"Template {template_id} was not deleted, API returned: {response.status_code}")
                return False
    
    except Exception as e:
        logger.error(f"Error in template deletion test: {e}")
        return False

def run_tests():
    """Run all E2E template tests"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        logger.info("Starting E2E template feature tests")
        
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
        if not register_and_login_api():
            logger.error("Registration/login test failed")
            return False
        logger.info("Registration and login successful")
        
        # Test template listing page
        if not test_template_listing_page():
            logger.error("Template listing page test failed")
            return False
        logger.info("Template listing page test passed")
        
        # Test template upload for different file types
        test_files = [
            {
                "path": os.path.join(TEMPLATE_DOCS_DIR, "template_data.csv"),
                "title": "E2E Test CSV Template",
                "doc_type": "other"
            },
            {
                "path": os.path.join(TEMPLATE_DOCS_DIR, "template_content.txt"),
                "title": "E2E Test TXT Template",
                "doc_type": "legal"
            },
            {
                "path": os.path.join(TEMPLATE_DOCS_DIR, "template_config.json"),
                "title": "E2E Test JSON Template",
                "doc_type": "contract"
            }
        ]
        
        for test_file in test_files:
            if not test_template_upload_page(test_file["path"], test_file["title"], test_file["doc_type"]):
                logger.error(f"Template upload test failed for {test_file['path']}")
                return False
            logger.info(f"Template upload test passed for {test_file['path']}")
        
        # Test viewing template details
        if not test_view_template_details():
            logger.error("Template details view test failed")
            return False
        logger.info("Template details view test passed")
        
        # Test template analysis
        if not test_analyze_template():
            logger.error("Template analysis test failed")
            return False
        logger.info("Template analysis test passed")
        
        # Test template filtering API
        if not test_filter_templates_api():
            logger.error("Template filtering API test failed")
            return False
        logger.info("Template filtering API test passed")
        
        # Test template deletion
        if not test_delete_template():
            logger.error("Template deletion test failed")
            return False
        logger.info("Template deletion test passed")
        
        logger.info("All E2E template feature tests completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"An unexpected error occurred during testing: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)