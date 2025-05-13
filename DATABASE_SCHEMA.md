# Database Schema Documentation

This document provides details about the database schema for the RapidocsAI application.

## Overview

The application uses SQLAlchemy ORM with SQLite for development and PostgreSQL for production. Alembic is used for database migrations.

## Tables

### Users

The `users` table stores user account information.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key, auto-incremented |
| username | String | Unique username for login |
| email | String | User's email address (unique) |
| hashed_password | String | Securely hashed user password |
| is_active | Boolean | Flag to indicate if user account is active |
| is_admin | Boolean | Flag to indicate if user has admin privileges |
| created_at | DateTime | Timestamp of user creation |
| updated_at | DateTime | Timestamp of last user update |

### Documents

The `documents` table stores metadata about uploaded documents.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key, auto-incremented |
| user_id | Integer | Foreign key to users.id, owner of the document |
| title | String | Document title |
| description | Text | Optional document description |
| doc_type | String | Type of document (legal, real_estate, contract, lease, other) |
| status | String | Processing status (uploaded, processing, processed, error) |
| original_filename | String | Original filename of the uploaded document |
| file_path | String | Path to the stored document file |
| file_content | Text | Extracted text content from the document |
| ai_analysis | Text | JSON string with AI analysis results |
| tag | String | Optional tag for categorizing documents (e.g., "template") |
| created_at | DateTime | Timestamp of document creation |
| updated_at | DateTime | Timestamp of last document update |

### Activity Logs

The `activity_logs` table records user actions for audit purposes.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key, auto-incremented |
| user_id | Integer | Foreign key to users.id, user who performed the action |
| action | String | Type of action (e.g., login, document_upload, document_processed) |
| description | Text | Human-readable description of the activity |
| ip_address | String | IP address from which the action was performed |
| details | Text | JSON string with additional details about the action |
| created_at | DateTime | Timestamp when the activity occurred |

## Relationships

- Each user can have multiple documents (one-to-many)
- Each user can have multiple activity logs (one-to-many)
- Documents do not have direct relationships to each other

## Tag System Details

The `tag` column in the `documents` table enables the template management system:

- When a document is uploaded with the tag "template", it is marked as a template document
- Template documents are used as reference examples for document transformation
- Documents can be filtered by their tag value
- By default, documents with no tag are considered regular documents
- Templates are excluded from regular document listings unless explicitly included

## Template Transformation

The document transformation process uses three documents:

1. Source document to be transformed
2. Input template document (similar format to the source document)
3. Output template document (target format for transformation)

The database relationships are maintained by document IDs referenced in API calls rather than through direct foreign keys.

## Schema Migrations

Changes to the database schema are managed using Alembic migrations.

### Major Migration Steps:

1. **Initial Schema** - Created base tables for users, documents, and activity logs
2. **Add Document Tag Field** - Added the tag column to support template functionality
3. **Add Document Status Field** - Added status tracking for document processing

Use `alembic upgrade head` to apply all migrations to the current database.