# RapidocsAI (v1.0)

This repository contains an AI-powered document management system with both a RESTful API and web frontend that allows users to authenticate, upload documents, analyze content, and manage their document library.

## Core Functionality

- User authentication (login, registration)
- Document upload and storage
- Document tagging system (including template tagging)
- Support for multiple file formats (PDF, DOCX, CSV, Excel, JSON, TXT)
- Document metadata extraction
- Document management (listing, retrieval, deletion)
- Admin functionality
- Database management utilities
- Command-line client for API interaction

## File Structure and Purpose

### Root Directory

- `alembic.ini` - Configuration file for Alembic (database migration tool)
- `requirements.txt` - Python dependencies for the application
- `run_dev.sh` - Script to run the development server
- `db_manage.py` - Command-line tool for database management
- `document_cli.py` - Command-line client for API interaction
- `readme.md` - This documentation file

### App Directory (Main Application Code)

- **app/main.py** - The main FastAPI application entry point
- **app/core/** - Core configuration files
  - `database.py` - Database connection and session setup
- **app/models/** - SQLAlchemy database models
  - `user.py` - User model for authentication
  - `document.py` - Document model for storing document information
  - `activity_log.py` - Activity logging model
- **app/routes/** - API routes (endpoints)
  - `auth.py` - Authentication endpoints (login, registration)
  - `users.py` - User management endpoints
  - `documents.py` - Document upload and management endpoints
  - `admin.py` - Administrative endpoints
- **app/schemas/** - Pydantic schemas for request/response validation
  - `user.py` - User schemas
  - `document.py` - Document schemas
  - `auth.py` - Authentication schemas
  - `activity_log.py` - Activity log schemas
- **app/services/** - Business logic services
  - `auth_service.py` - Authentication service (JWT tokens, password hashing)
  - `document_service.py` - Document processing service
  - `activity_service.py` - Activity logging service
- **app/utils/** - Utility functions
  - `document_processor.py` - Document text extraction and metadata extraction
- **app/frontend/** - Web frontend
  - `__init__.py` - Frontend router and route handlers
  - **templates/** - Jinja2 HTML templates
    - `layout.html` - Base template with common elements
    - `index.html` - Homepage
    - `login.html` - Login page
    - `register.html` - Registration page
    - `documents.html` - Document listing and management
    - `upload.html` - Document upload form
    - `templates.html` - Template document listing
    - `template_upload.html` - Template document upload form
  - **static/** - Static assets
    - **css/** - Stylesheet files
    - **js/** - JavaScript files
- **app/scripts/** - Utility scripts and tools
  - **db/** - Database management scripts
    - `reset_database.py` - Script to reset and recreate the database
    - `verify_database.py` - Script to verify database integrity
    - `manage_db.py` - CLI tool for database management
  - **client/** - API client tools
    - `document_client.py` - Command-line client for API interaction

### Database Migration (Alembic)

- **alembic/** - Database migration scripts
  - `versions/` - Contains individual migration scripts
    - `02a995935fe7_initial_schema.py` - Database schema definition

### Tests

- **tests/** - Test files
  - `test_api.py` - Basic API endpoint tests
  - `test_document_features.py` - Document feature tests
  - `test_template_features.py` - Template tagging and filtering tests
  - `test_e2e_template_features.py` - End-to-end Selenium tests for template UI
  - **scripts/** - Test execution scripts
    - `run_tests.sh` - Script to run API and document tests
    - `run_template_tests.sh` - Script to run template tests
    - `run_e2e_tests.sh` - Script to run end-to-end tests
  - **sample_docs/** - Sample documents for testing
    - `input_depo.pdf` - Sample deposition document
    - `output_depo.csv` - Sample output file
    - `sample_contract.docx` - Sample contract document
    - **templates/** - Template files for testing
      - `template_data.csv` - CSV template data
      - `template_content.txt` - Text template content
      - `template_config.json` - JSON template configuration
      - `template_data.xlsx` - Excel template data

### Data Storage

- **uploads/** - Directory where uploaded documents are stored
- **logs/** - Directory for application logs
- **outputs/** - Directory for any output files

## Key Components (Data Flow)

```
                             +------------------+
                             |                  |
                             |   User Input     |
                             |  (Document File) |
                             |                  |
                             +--------+---------+
                                      |
                                      v
                             +------------------+
                             |                  |
                             |   API/Backend    |
                             |                  |
                             +------------------+
                                      |
                                      v
                             +------------------+
                             |                  |
                             | Document Storage |
                             |                  |
                             +------------------+
```

### Data Flow Explanation:

1. User uploads a document via the API
2. The API processes the document (extracts text and metadata)
3. The document is stored in the database and file system
4. User can retrieve or manage their documents

## Usage

### Run the application locally
```bash
./run_dev.sh
```

### Access the Web Interface
```
http://localhost:8000/
```

### Access the Swagger documentation
```
http://localhost:8000/docs
```

### Deploy to Heroku

The application is fully compatible with Heroku deployment. You can deploy in one of the following ways:

#### Option 1: Deploy using the helper script
```bash
# Make sure the script is executable
chmod +x deploy_heroku.sh

# Run the deployment script
./deploy_heroku.sh
```

#### Option 2: Deploy manually

1. Create a Heroku app
```bash
heroku create rapidocsai
```

2. Add PostgreSQL addon
```bash
heroku addons:create heroku-postgresql:mini
```

3. Configure environment variables
```bash
heroku config:set JWT_SECRET_KEY=your_secure_jwt_secret
heroku config:set OPENAI_API_KEY=your_openai_api_key
heroku config:set USE_S3_STORAGE=true
heroku config:set AWS_ACCESS_KEY_ID=your_aws_access_key
heroku config:set AWS_SECRET_ACCESS_KEY=your_aws_secret_key
heroku config:set AWS_REGION=us-east-1
heroku config:set S3_BUCKET_NAME=your-s3-bucket
heroku config:set ENVIRONMENT=production
```

4. Push code to Heroku
```bash
git push heroku master
```

5. Run database migrations
```bash
heroku run python -m alembic upgrade head
```

#### Option 3: Deploy with the Heroku button

You can also deploy directly to Heroku by clicking the button below:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

#### Important Heroku Deployment Notes:

- **File Storage**: When deploying to Heroku, you must set `USE_S3_STORAGE=true` and configure AWS S3 since Heroku's filesystem is ephemeral.
- **Database**: The application automatically configures to use Heroku PostgreSQL.
- **Environment Variables**: All configuration is done through environment variables (config vars in Heroku).
- **Monitoring**: Use `heroku logs --tail` to monitor application logs.

### Authentication
The API uses JWT for authentication. To access protected endpoints:
1. Register a user at `/auth/register`
2. Login at `/auth/login` to receive an access token
3. Use the token in the Authorization header for subsequent requests

### Document Upload
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@path/to/your/document.pdf" \
  -F "title=Document Title" \
  -F "description=Document Description" \
  -F "doc_type=legal" \
  -F "tag=template"  # Optional: tag the document (e.g., as a template)
```

Supported file formats: PDF, DOCX, CSV, Excel (.xlsx), JSON, and plain text (.txt)

### Document Transformation with Templates
```bash
# First upload your document and templates
# Then transform a document using templates
curl -X POST "http://localhost:8000/documents/1/transform-with-templates" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_input_id": 2,
    "template_output_id": 3
  }'
```

Note: Templates must be tagged with the "template" tag when uploaded.

## Testing
 
### Testing Infrastructure

The application includes a comprehensive testing infrastructure with different types of tests:

1. **API Tests** (`test_api.py`)
   - Tests basic API endpoints including authentication, document upload, and retrieval
   - Verifies correct response codes and data structures
   - Uses pytest fixtures for database setup/teardown and authentication

2. **Document Feature Tests** (`test_document_features.py`)
   - Tests core document processing functionality
   - Verifies file upload for different document types
   - Tests metadata extraction and document analysis
   - Ensures proper storage and retrieval of documents

3. **Template Feature Tests** (`test_template_features.py`)
   - Tests the document tagging system with focus on template functionality
   - Verifies proper filtering of documents by tag
   - Tests template-specific endpoints and features
   - Ensures templates don't appear in regular document lists

4. **End-to-End Tests** (`test_e2e_template_features.py`)
   - Uses Selenium WebDriver for browser-based testing
   - Tests the complete user flow from login to template management
   - Verifies template listing, uploading, viewing, and deletion through the web UI
   - Includes tests for proper alert handling and confirmation dialogs

### Running Tests

The application includes several test scripts:

```bash
# Run API and document feature tests
./tests/scripts/run_tests.sh

# Run template feature tests
./tests/scripts/run_template_tests.sh

# Run end-to-end UI tests (requires Chrome)
./tests/scripts/run_e2e_tests.sh
```

### Test Structure

- **Test Location**: All tests are located in the `/tests` directory
- **Sample Documents**: Test documents are stored in `/tests/sample_docs`
- **Test Scripts**: Execution scripts are in `/tests/scripts`

### Test Dependencies

End-to-end tests require additional dependencies:
- Selenium
- ChromeDriver
- webdriver_manager

These dependencies are automatically installed by the test scripts if not already present.

## Command-line Tools

### Document Client
The document client provides a simple interface for interacting with the API:

```bash
# Register a new user
python document_cli.py register --email user@example.com --username user --password Password123

# Login and get a token
python document_cli.py list --username user --password Password123

# Upload a document
python document_cli.py upload --file path/to/document.pdf --title "Document Title" --description "Description" --doc-type legal

# Upload a template
python document_cli.py upload --file path/to/template.pdf --title "Template" --description "Template file" --doc-type legal --tag template

# List all documents
python document_cli.py list

# List only templates
python document_cli.py list --tag template

# Get document details
python document_cli.py get --id 1

# Get document analysis
python document_cli.py analysis --id 1

# Transform document using templates
python document_cli.py transform --id 1 --input-template 2 --output-template 3

# Delete a document
python document_cli.py delete --id 1
```

### Database Management
The database management tool provides utilities for managing the database:

```bash
# Show database information
python db_manage.py info

# Reset the database (delete all data and recreate tables)
python db_manage.py reset

# Reset the database and recreate migrations
python db_manage.py reset --with-migrations

# Verify database integrity
python db_manage.py verify
```

## Web Interface

The application includes a complete web frontend with the following pages:

- **Home** - Landing page with information about the system
- **Login/Register** - User authentication pages
- **Documents** - List and manage uploaded documents
- **Upload** - Form for uploading new documents with integrated template selection
- **Template Management** - Dedicated pages for template upload and management
- **Document Analysis** - Interactive analysis of document content and metadata
- **Document Transformation** - Transform documents using input and output templates

The web interface is responsive and works on both desktop and mobile devices.

### Enhanced Document Upload Interface

The document upload interface provides a streamlined workflow:

1. **Document Details Tab**
   - Enter document metadata (title, description, type)
   - Upload document file
   
2. **Template Selection Tab**
   - Select input and output templates from existing templates
   - Option to upload new templates directly if needed
   - Add input/output templates on-the-fly without leaving the upload process

3. **Post-Upload Actions**
   - Analyze document content and metadata
   - Transform document using selected templates
   - View all documents in library

### Template System

The application includes a comprehensive tagging system that allows documents to be categorized, with special support for template documents:

- Documents can be tagged during upload using the "tag" parameter
- A special "template" tag is used to designate template documents
- Template documents can be filtered separately from regular documents
- Templates can be used as reference patterns for document transformation and analysis
- The system supports templates in multiple formats (PDF, DOCX, CSV, Excel, JSON, TXT)
- The web interface includes dedicated template upload and browsing pages
- Users can select input and output templates during document upload
- Templates can be uploaded directly from the document upload page
- Document transformation can be performed immediately after upload

## API Endpoints

- **Authentication**
  - POST `/auth/register` - Register a new user
  - POST `/auth/login` - Login and get access token

- **Documents**
  - POST `/documents/upload` - Upload a document (supports tagging via "tag" parameter)
  - GET `/documents/` - List user's documents (supports filtering by tag, including "template")
  - GET `/documents/{document_id}` - Get a document
  - GET `/documents/{document_id}/analysis` - Get document analysis
  - POST `/documents/{document_id}/transform-with-templates` - Transform a document using input and output templates
  - POST `/documents/generate` - Generate a document
  - DELETE `/documents/{document_id}` - Delete a document

- **Admin**
  - GET `/admin/users` - List all users (admin only)
  - GET `/admin/documents` - List all documents (admin only)
  - POST `/admin/users/{user_id}/activate` - Activate a user (admin only)
  - POST `/admin/users/{user_id}/deactivate` - Deactivate a user (admin only)