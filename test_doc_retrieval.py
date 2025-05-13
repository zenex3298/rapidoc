import requests
import json
import sys

# Note: We'll use the same credentials from the previous script
# This is a simplified version to fetch the latest document
try:
    # Login again
    login_data = {
        'username': 'uploadtest_1747164380',  # Using the latest username from DB
        'password': 'TestPassword123'
    }
    
    print('Logging in...')
    response = requests.post('http://localhost:8000/auth/login', data=login_data)
    
    if response.status_code != 200:
        print(f'Login failed: {response.text}')
        sys.exit(1)
        
    token_data = response.json()
    access_token = token_data['access_token']
    print('Login successful, received token')
    
    # Get all user documents
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('http://localhost:8000/documents/', headers=headers)
    
    if response.status_code != 200:
        print(f'Failed to retrieve documents: {response.text}')
        sys.exit(1)
    
    documents = response.json()
    print(f'Found {len(documents)} documents')
    
    if documents:
        # Get the most recent document (first in the list)
        latest_doc = documents[0]
        doc_id = latest_doc['id']
        
        # Get the document analysis
        response = requests.get(f'http://localhost:8000/documents/{doc_id}/analysis', headers=headers)
        
        if response.status_code == 200:
            analysis = response.json()
            print(f'Document analysis retrieved for document {doc_id}')
            print(f'Analysis summary: {json.dumps(analysis, indent=2)[:200]}...')
        else:
            print(f'Failed to retrieve analysis: {response.text}')
    else:
        print('No documents found')
        
except Exception as e:
    print(f'Error during document testing: {e}')