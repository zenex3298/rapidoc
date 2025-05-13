# RapidocsAI API Documentation

This document provides detailed information about the RapidocsAI API, including endpoints, parameters, and examples.

## Base URL

All API endpoints are relative to the base URL:

```
http://localhost:8000/
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Register a New User

```
POST /auth/register
```

**Request Body:**
```json
{
  "username": "user",
  "email": "user@example.com",
  "password": "Password123"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "user",
  "email": "user@example.com",
  "is_active": true,
  "is_admin": false,
  "created_at": "2025-05-01T10:00:00"
}
```

### Login

```
POST /auth/login
```

**Request Body:**
```json
{
  "username": "user",
  "password": "Password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

The access token should be included in the `Authorization` header for all subsequent requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Document Endpoints

### Upload Document

```
POST /documents/upload
```

**Request:**
- Content-Type: multipart/form-data
- Authorization header required

**Form Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | File | Yes | The document file to upload |
| title | String | Yes | Document title |
| description | String | No | Document description |
| doc_type | String | Yes | Document type (legal, real_estate, contract, lease, other) |
| tag | String | No | Optional tag for the document (e.g., "template") |

**Response:**
```json
{
  "id": 1,
  "title": "Document Title",
  "description": "Document Description",
  "doc_type": "legal",
  "status": "uploaded",
  "original_filename": "document.pdf",
  "user_id": 1,
  "tag": "template",
  "created_at": "2025-05-01T10:30:00",
  "updated_at": "2025-05-01T10:30:00"
}
```

### List Documents

```
GET /documents/
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| skip | Integer | No | Number of records to skip (default: 0) |
| limit | Integer | No | Maximum number of records to return (default: 100) |
| status | String | No | Filter by status |
| doc_type | String | No | Filter by document type |
| include_templates | Boolean | No | Include template documents (default: false) |
| tag | String | No | Filter by specific tag |

**Response:**
```json
[
  {
    "id": 1,
    "title": "Document Title",
    "description": "Document Description",
    "doc_type": "legal",
    "status": "processed",
    "original_filename": "document.pdf",
    "user_id": 1,
    "tag": null,
    "created_at": "2025-05-01T10:30:00",
    "updated_at": "2025-05-01T10:30:00"
  },
  ...
]
```

### Get Document

```
GET /documents/{document_id}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| document_id | Integer | ID of the document to retrieve |

**Response:**
```json
{
  "id": 1,
  "title": "Document Title",
  "description": "Document Description",
  "doc_type": "legal",
  "status": "processed",
  "original_filename": "document.pdf",
  "user_id": 1,
  "tag": null,
  "created_at": "2025-05-01T10:30:00",
  "updated_at": "2025-05-01T10:30:00"
}
```

### Get Document Analysis

```
GET /documents/{document_id}/analysis
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| document_id | Integer | ID of the document to analyze |

**Response:**
```json
{
  "metadata": {
    "page_count": 5,
    "file_size_kb": 256.5,
    "title": "Document Title",
    "author": "Author Name",
    "structure_info": {
      "pages": [
        {
          "page_number": 1,
          "character_count": 1500,
          "potential_headings": ["Introduction", "Background"]
        },
        ...
      ]
    }
  },
  "processing_time_seconds": 1.25
}
```

### Transform Document with Templates

```
POST /documents/{document_id}/transform-with-templates
```

The transformation is performed asynchronously, and the endpoint returns a job ID that can be used to check the status of the transformation.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| document_id | Integer | ID of the document to transform |

**Request Body:**
```json
{
  "template_input_id": 2,
  "template_output_id": 3
}
```

**Response:**
```json
{
  "status": "queued",
  "message": "Document transformation job has been queued",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_id": 1,
  "document_title": "Source Document",
  "template_input_id": 2,
  "template_input_title": "Input Template",
  "template_output_id": 3,
  "template_output_title": "Output Template",
  "check_status_url": "/jobs/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-05-01T11:15:00"
}
```

## Job Management

Document transformations and other long-running tasks are processed asynchronously in the background. The API provides endpoints to check the status of these jobs and retrieve their results.

### List Jobs

```
GET /jobs/
```

List jobs for the current user.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | Integer | No | Maximum number of jobs to return (default: 10) |

**Response:**
```json
[
  {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 1,
    "document_id": 1,
    "template_input_id": 2,
    "template_output_id": 3,
    "status": "completed",
    "created_at": "2025-05-01T11:15:00",
    "updated_at": "2025-05-01T11:16:30"
  },
  {
    "job_id": "660e8400-e29b-41d4-a716-446655440001",
    "user_id": 1,
    "document_id": 4,
    "template_input_id": 2,
    "template_output_id": 3,
    "status": "processing",
    "created_at": "2025-05-01T11:20:00",
    "updated_at": "2025-05-01T11:20:05"
  }
]
```

### Get Job Status

```
GET /jobs/{job_id}
```

Get the status and result of a specific job.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| job_id | String | ID of the job to check |

**Response for a queued or processing job:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "document_id": 1,
  "template_input_id": 2,
  "template_output_id": 3,
  "status": "processing",
  "created_at": "2025-05-01T11:15:00",
  "updated_at": "2025-05-01T11:15:30"
}
```

**Response for a completed job:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "document_id": 1,
  "template_input_id": 2,
  "template_output_id": 3,
  "status": "completed",
  "created_at": "2025-05-01T11:15:00",
  "updated_at": "2025-05-01T11:16:30",
  "result": {
    "status": "success",
    "document_id": 1,
    "document_title": "Source Document",
    "template_input_id": 2,
    "template_input_title": "Input Template",
    "template_output_id": 3,
    "template_output_title": "Output Template",
    "transformed_content": "This is the transformed content based on the templates...",
    "download_path": "/documents/downloads/transformed_789.csv",
    "timestamp": "2025-05-01T11:16:30",
    "formats": {
      "document": ".pdf",
      "template_input": ".pdf",
      "template_output": ".csv",
      "output": ".csv"
    },
    "file_type": "csv",
    "message": "Document transformation completed"
  }
}
```

**Response for a failed job:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "document_id": 1,
  "template_input_id": 2,
  "template_output_id": 3,
  "status": "error",
  "created_at": "2025-05-01T11:15:00",
  "updated_at": "2025-05-01T11:16:30",
  "result": {
    "error": "Error message",
    "document_id": 1,
    "document_title": "Source Document",
    "message": "Error during document transformation"
  }
}
```

### Delete Document

```
DELETE /documents/{document_id}
```

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| document_id | Integer | ID of the document to delete |

**Response:**
No content (204)

## Template Functionality

### How Templates Work

1. **Tagging Documents as Templates:**
   - When uploading a document, set the "tag" parameter to "template"
   - The document will be marked as a template and won't appear in regular document listings

2. **Listing Templates:**
   - Use the GET `/documents/` endpoint with `tag=template` parameter
   - Alternatively, use `include_templates=true` to include templates with regular documents

3. **Template Transformation:**
   - Templates provide input and output examples for document transformation
   - Use the POST `/documents/{document_id}/transform-with-templates` endpoint
   - Specify both an input template ID and output template ID
   - The system transforms the document from the input format to the output format

### Template Selection API

During document upload through the web interface, the client displays available templates and allows the user to:

1. Select an existing input template
2. Select an existing output template
3. Upload new templates directly during the document upload process

These selections are stored on the client side and used when calling the transformation endpoint.

## Error Handling

API errors are returned with appropriate HTTP status codes and error details:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

Common error codes:
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Unprocessable Entity
- 500: Internal Server Error

## Pagination

List endpoints support pagination using `skip` and `limit` parameters.

## Admin Endpoints

Admin endpoints are only accessible to users with `is_admin` set to true:

```
GET /admin/users
GET /admin/documents
POST /admin/users/{user_id}/activate
POST /admin/users/{user_id}/deactivate
```