import requests
import json
import os
import sys
import time
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TEST_USER = {
    'email': f'test_{int(time.time())}@example.com',
    'username': f'testuser_{int(time.time())}',
    'password': 'TestPassword123'
}

def test_health_check():
    """Test health check endpoint"""
    logger.info("Testing health check endpoint")
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        logger.info("Health check test passed")
        return True
    except Exception as e:
        logger.error(f"Health check test failed: {e}")
        return False

def test_user_registration():
    """Test user registration"""
    logger.info(f"Testing user registration with username: {TEST_USER['username']}")
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == TEST_USER["email"]
        assert user_data["username"] == TEST_USER["username"]
        logger.info("User registration test passed")
        return True
    except Exception as e:
        logger.error(f"User registration test failed: {e}")
        return False

def test_user_login():
    """Test user login and token generation"""
    logger.info(f"Testing user login with username: {TEST_USER['username']}")
    try:
        login_data = {
            'username': TEST_USER['username'],
            'password': TEST_USER['password']
        }
        response = requests.post(
            f"{BASE_URL}/auth/login", 
            data=login_data
        )
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        logger.info("User login test passed")
        return token_data["access_token"]
    except Exception as e:
        logger.error(f"User login test failed: {e}")
        return None

def test_protected_endpoint(token):
    """Test protected endpoint with JWT token"""
    logger.info("Testing protected endpoint (user profile)")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f"{BASE_URL}/users/me", headers=headers)
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["email"] == TEST_USER["email"]
        assert user_data["username"] == TEST_USER["username"]
        logger.info("Protected endpoint test passed")
        return True
    except Exception as e:
        logger.error(f"Protected endpoint test failed: {e}")
        return False

def run_tests():
    """Run all tests"""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        logger.info("Starting API tests")
        
        # Test 1: Health Check
        if not test_health_check():
            logger.error("Health check test failed. Make sure the server is running.")
            return False
        
        # Test 2: User Registration
        if not test_user_registration():
            logger.error("User registration test failed")
            return False
        
        # Test 3: User Login
        token = test_user_login()
        if not token:
            logger.error("User login test failed")
            return False
        
        # Test 4: Protected Endpoint
        if not test_protected_endpoint(token):
            logger.error("Protected endpoint test failed")
            return False
        
        logger.info("All tests passed successfully!")
        return True
    
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to the server. Make sure the server is running.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)