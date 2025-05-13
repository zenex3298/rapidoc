#!/usr/bin/env python3
"""
Document Management API Client

A script to interact with the Document Management API, handling authentication
and document operations in a single command.
"""

import os
import sys
import json
import argparse
import requests
from typing import Dict, Any, Optional, List, Tuple

# API Configuration
API_URL = "http://localhost:8000"
TOKEN_FILE = ".auth_token.json"

def save_token(token_data: Dict[str, str]) -> None:
    """Save the authentication token to a file"""
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)
    # Make file readable only by user
    os.chmod(TOKEN_FILE, 0o600)
    print(f"Token saved to {TOKEN_FILE}")

def load_token() -> Optional[Dict[str, str]]:
    """Load the authentication token from file if it exists"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Error: Invalid token file, will re-authenticate")
    return None

def login(username: str, password: str) -> str:
    """Authenticate with the API and return the access token"""
    url = f"{API_URL}/auth/login"
    data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code != 200:
        print(f"Error: Authentication failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    token_data = response.json()
    save_token(token_data)
    return token_data["access_token"]

def register(email: str, username: str, password: str) -> Dict[str, Any]:
    """Register a new user with the API"""
    url = f"{API_URL}/auth/register"
    data = {
        "email": email,
        "username": username,
        "password": password
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code != 201:
        print(f"Error: Registration failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    return response.json()

def upload_document(token: str, file_path: str, title: str, description: str, doc_type: str) -> Dict[str, Any]:
    """Upload a document to the API"""
    url = f"{API_URL}/documents/upload"
    headers = {"Authorization": f"Bearer {token}"}
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {
            "title": title,
            "description": description,
            "doc_type": doc_type
        }
        
        response = requests.post(url, headers=headers, files=files, data=data)
    
    if response.status_code != 201:
        print(f"Error: Upload failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    return response.json()

def list_documents(token: str, status: Optional[str] = None, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List documents from the API"""
    url = f"{API_URL}/documents/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {}
    
    if status:
        params["status"] = status
    if doc_type:
        params["doc_type"] = doc_type
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Error: List failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    return response.json()

def get_document(token: str, document_id: int) -> Dict[str, Any]:
    """Get a specific document from the API"""
    url = f"{API_URL}/documents/{document_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Get document failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    return response.json()

def get_document_analysis(token: str, document_id: int) -> Dict[str, Any]:
    """Get document analysis from the API"""
    url = f"{API_URL}/documents/{document_id}/analysis"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Get analysis failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    return response.json()

def delete_document(token: str, document_id: int) -> None:
    """Delete a document from the API"""
    url = f"{API_URL}/documents/{document_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code != 204:
        print(f"Error: Delete failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    print(f"Document {document_id} deleted successfully")

def generate_document(token: str, template_type: str, input_data: Dict[str, Any], 
                    title: Optional[str] = None, 
                    description: Optional[str] = None, 
                    content: Optional[str] = None) -> Dict[str, Any]:
    """Generate a document using the API"""
    url = f"{API_URL}/documents/generate"
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "template_type": template_type,
        "input_data": json.dumps(input_data)
    }
    
    if title:
        data["title"] = title
    if description:
        data["description"] = description
    if content:
        data["content"] = content
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code != 200:
        print(f"Error: Generate document failed ({response.status_code})")
        print(response.text)
        sys.exit(1)
    
    return response.json()

def main() -> None:
    """Parse arguments and dispatch to the appropriate handler"""
    # Create the main parser
    parser = argparse.ArgumentParser(description="Document Management API Client")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Register subcommand
    register_parser = subparsers.add_parser("register", help="Register a new user")
    register_parser.add_argument("--email", required=True, help="Email address")
    register_parser.add_argument("--username", required=True, help="Username")
    register_parser.add_argument("--password", required=True, help="Password")
    
    # Upload subcommand
    upload_parser = subparsers.add_parser("upload", help="Upload a document")
    upload_parser.add_argument("--file", required=True, help="Path to the file to upload")
    upload_parser.add_argument("--title", required=True, help="Document title")
    upload_parser.add_argument("--description", help="Document description")
    upload_parser.add_argument("--doc-type", required=True, choices=["legal", "real_estate", "contract", "lease", "other"], 
                            help="Document type")
    upload_parser.add_argument("--username", help="Username for authentication")
    upload_parser.add_argument("--password", help="Password for authentication")
    upload_parser.add_argument("--force-login", action="store_true", help="Force login even if token exists")
    
    # List subcommand
    list_parser = subparsers.add_parser("list", help="List documents")
    list_parser.add_argument("--status", choices=["uploaded", "processing", "processed", "error"], 
                          help="Filter by status")
    list_parser.add_argument("--doc-type", choices=["legal", "real_estate", "contract", "lease", "other"],
                          help="Filter by document type")
    list_parser.add_argument("--output", help="Save output to a file")
    list_parser.add_argument("--username", help="Username for authentication")
    list_parser.add_argument("--password", help="Password for authentication")
    list_parser.add_argument("--force-login", action="store_true", help="Force login even if token exists")
    
    # Get subcommand
    get_parser = subparsers.add_parser("get", help="Get a document")
    get_parser.add_argument("--id", type=int, required=True, help="Document ID")
    get_parser.add_argument("--output", help="Save output to a file")
    get_parser.add_argument("--username", help="Username for authentication")
    get_parser.add_argument("--password", help="Password for authentication")
    get_parser.add_argument("--force-login", action="store_true", help="Force login even if token exists")
    
    # Analysis subcommand
    analysis_parser = subparsers.add_parser("analysis", help="Get document analysis")
    analysis_parser.add_argument("--id", type=int, required=True, help="Document ID")
    analysis_parser.add_argument("--output", help="Save output to a file")
    analysis_parser.add_argument("--username", help="Username for authentication")
    analysis_parser.add_argument("--password", help="Password for authentication")
    analysis_parser.add_argument("--force-login", action="store_true", help="Force login even if token exists")
    
    # Delete subcommand
    delete_parser = subparsers.add_parser("delete", help="Delete a document")
    delete_parser.add_argument("--id", type=int, required=True, help="Document ID")
    delete_parser.add_argument("--username", help="Username for authentication")
    delete_parser.add_argument("--password", help="Password for authentication")
    delete_parser.add_argument("--force-login", action="store_true", help="Force login even if token exists")
    
    # Generate subcommand
    generate_parser = subparsers.add_parser("generate", help="Generate a document")
    generate_parser.add_argument("--template-type", required=True, 
                              choices=["legal_contract", "real_estate_agreement", "lease_agreement", "other"],
                              help="Template type")
    generate_parser.add_argument("--title", help="Document title")
    generate_parser.add_argument("--description", help="Document description")
    generate_parser.add_argument("--input-data-file", help="JSON file with input data for generation")
    generate_parser.add_argument("--content-file", help="File containing document content")
    generate_parser.add_argument("--output", help="Save output to a file")
    generate_parser.add_argument("--username", help="Username for authentication")
    generate_parser.add_argument("--password", help="Password for authentication")
    generate_parser.add_argument("--force-login", action="store_true", help="Force login even if token exists")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Handle registration if requested
    if args.command == "register":
        register(args.email, args.username, args.password)
        print(f"User {args.username} registered successfully")
        return
    
    # Get token (from saved file or by logging in)
    token_data = load_token()
    token = token_data.get("access_token") if token_data else None
    
    # Check if we need to login
    if not token or getattr(args, "force_login", False):
        if not getattr(args, "username", None) or not getattr(args, "password", None):
            print("Error: Username and password required for login")
            sys.exit(1)
        token = login(args.username, args.password)
    
    # Handle document commands
    if args.command == "upload":
        if not all([args.file, args.title, args.doc_type]):
            print("Error: File, title, and doc_type are required for upload")
            sys.exit(1)
        result = upload_document(token, args.file, args.title, args.description or "", args.doc_type)
        print(f"Document uploaded successfully, ID: {result['id']}")
        print(json.dumps(result, indent=2))

    elif args.command == "list":
        documents = list_documents(token, getattr(args, "status", None), getattr(args, "doc_type", None))
        print(f"Found {len(documents)} documents:")
        for doc in documents:
            print(f"ID: {doc['id']} | Title: {doc['title']} | Status: {doc['status']} | Type: {doc['doc_type']}")
        
        if getattr(args, "output", None):
            with open(args.output, "w") as f:
                json.dump(documents, f, indent=2)
            print(f"Documents list saved to {args.output}")

    elif args.command == "get":
        if not args.id:
            print("Error: Document ID is required")
            sys.exit(1)
        document = get_document(token, args.id)
        print(f"Document ID: {document['id']}, Title: {document['title']}")
        print(json.dumps(document, indent=2))
        
        if getattr(args, "output", None):
            with open(args.output, "w") as f:
                json.dump(document, f, indent=2)
            print(f"Document details saved to {args.output}")

    elif args.command == "analysis":
        if not args.id:
            print("Error: Document ID is required")
            sys.exit(1)
        analysis = get_document_analysis(token, args.id)
        print(f"Analysis for document ID: {args.id}")
        print(json.dumps(analysis, indent=2))
        
        if getattr(args, "output", None):
            with open(args.output, "w") as f:
                json.dump(analysis, f, indent=2)
            print(f"Analysis saved to {args.output}")

    elif args.command == "delete":
        if not args.id:
            print("Error: Document ID is required")
            sys.exit(1)
        delete_document(token, args.id)

    elif args.command == "generate":
        if not args.template_type:
            print("Error: Template type is required")
            sys.exit(1)
        
        input_data = {}
        if getattr(args, "input_data_file", None):
            with open(args.input_data_file, "r") as f:
                input_data = json.load(f)
        
        content = None
        if getattr(args, "content_file", None):
            with open(args.content_file, "r") as f:
                content = f.read()
        
        result = generate_document(
            token, 
            args.template_type, 
            input_data,
            getattr(args, "title", None),
            getattr(args, "description", None),
            content
        )
        print(f"Document generated successfully, ID: {result['document_id']}")
        print(json.dumps(result, indent=2))
        
        if getattr(args, "output", None):
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Generation result saved to {args.output}")

if __name__ == "__main__":
    main()