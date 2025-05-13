# Claude Instructions

## Scalability
To ensure the model stays on track and maintains strict adherence to long-term goals without deviation, consider these prompts:

1. **Strict Alignment with Long-Term Vision**  
"Before making any changes, verify that the proposed modification directly aligns with the long-term project vision. No changes should be made if they introduce unnecessary complexity, redundancy, or misalignment with the core architecture."

2. **Justification for Every Line of Code**  
"Every line of code must have a clear, justified purpose that contributes to the overall project structure. If a change does not have a specific, documented rationale tied to project goals, it should not be made."

3. **Minimal, Tested, and Validated Additions Only**  
"No new code should be added unless it has been rigorously tested, reviewed, and proven necessary. Avoid speculative coding, temporary fixes, or features that are not validated by real needs or use cases."

4. **No Shortcuts or Unnecessary Dependencies**  
"Ensure that no shortcuts, workarounds, or unnecessary dependencies are introduced. Every solution must be maintainable, modular, and scalable in the long term. If a quick fix is required, document it and plan a proper implementation within the project roadmap."

5. **Preserve Code Simplicity and Clarity**  
"Every change should improve or maintain the clarity and simplicity of the codebase. If a proposed modification makes the system harder to understand or maintain, reconsider the approach or refactor the existing implementation instead."

6. **Consistency with Existing Architecture and Documentation**  
"Before implementing changes, ensure that they are consistent with the existing architecture and documentation. If discrepancies arise, update documentation first before modifying the code to maintain alignment across the project."

7. **Continuous Review and Feedback Process**  
"No change should be merged without thorough review and feedback from at least one other contributor. Regularly revisit previous decisions to ensure ongoing alignment with the project's goals."

8. **Prioritize Stability Over Speed**  
"Never prioritize speed at the expense of stability. Every change must be evaluated for its impact on the system's reliability, maintainability, and long-term integrity before implementation."

9. **Reject Features That Do Not Fit the Core Purpose**  
"Every feature or enhancement must pass a strict 'core purpose test.' If it does not directly support the fundamental objectives of the project, it should be deferred or rejected outright."

10. **Track All Changes and Revisit Past Decisions**  
"Every modification must be documented with a clear rationale and linked to a long-term strategy. Regularly review past decisions to ensure they still align with the evolving project vision."

By applying these prompts consistently, you can ensure the model remains disciplined, avoids unnecessary deviation, and stays fully aligned with the long-term objectives of the project.

## Heroku Deployment Checklist

Follow these steps for a successful Heroku deployment:

1. **Ensure Environment Variables**
   - Configure all environment variables through Heroku config vars
   - Must set: DATABASE_URL, JWT_SECRET_KEY, OPENAI_API_KEY, etc.
   - For S3 storage: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME, USE_S3_STORAGE=true
   - Redis configuration provided by REDIS_URL (added automatically by Redis add-on)

2. **Database Configuration**
   - Add PostgreSQL addon: `heroku addons:create heroku-postgresql:mini`
   - Configure DATABASE_URL automatically
   - Run migrations after deployment: `heroku run python -m alembic upgrade head`
   
3. **Redis Configuration**
   - Add Redis addon: `heroku addons:create heroku-redis:hobby-dev`
   - This automatically sets the REDIS_URL environment variable
   - Required for background job processing system

4. **File Storage Configuration**
   - Must set USE_S3_STORAGE=true for production
   - Configure proper AWS credentials and S3 bucket
   - All file uploads go to S3 instead of ephemeral filesystem

5. **Logging Configuration**
   - Logs go to stdout/stderr in production
   - Configure LOG_LEVEL if needed (defaults to INFO)
   - Use `heroku logs --tail` to monitor application logs

6. **Worker Configuration**
   - Scale worker dyno to at least 1: `heroku ps:scale worker=1`
   - Worker processes document transformations in the background
   - This allows transformations to run longer than the 30-second HTTP request timeout

7. **Deployment Steps**
   ```bash
   # Create Heroku app
   heroku create rapidocsai

   # Add PostgreSQL addon
   heroku addons:create heroku-postgresql:mini

   # Add Redis addon
   heroku addons:create heroku-redis:hobby-dev

   # Configure environment variables
   heroku config:set JWT_SECRET_KEY=your_secure_jwt_secret
   heroku config:set OPENAI_API_KEY=your_openai_api_key
   heroku config:set USE_S3_STORAGE=true
   heroku config:set AWS_ACCESS_KEY_ID=your_aws_access_key
   heroku config:set AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   heroku config:set AWS_REGION=us-east-1
   heroku config:set S3_BUCKET_NAME=your-s3-bucket
   heroku config:set ENVIRONMENT=production

   # Push code to Heroku
   git push heroku master

   # Run database migrations
   heroku run python -m alembic upgrade head

   # Scale the worker dyno
   heroku ps:scale worker=1

   # Check logs
   heroku logs --tail
   ```

8. **Maintenance and Monitoring**
   - Monitor application logs: `heroku logs --tail`
   - Check app status: `heroku ps`
   - Access PostgreSQL: `heroku pg:psql`
   - Restart application: `heroku restart`

## S3 Storage Integration

### Setup and Configuration

The application supports both local file storage and AWS S3 storage. S3 storage is recommended for production deployments, especially on platforms like Heroku with ephemeral filesystems.

#### Environment Variables

To enable S3 storage, set the following environment variables:

```
USE_S3_STORAGE=true
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1  # or your preferred region
S3_BUCKET_NAME=your-bucket-name
```

These can be added to a `.env` file in the project root during development or configured as environment variables in your deployment platform.

#### Testing S3 Configuration

Several test scripts are available to verify your S3 configuration:

1. `s3_test.sh` - Shell script for testing via AWS CLI
2. `simple_s3_test.py` - Basic Python script for testing with boto3
3. `test_s3.py` - Test script using the application's S3StorageService

To run the tests, ensure your environment variables are set and execute the scripts. For example:

```bash
# Make the shell script executable
chmod +x s3_test.sh

# Run the shell script
./s3_test.sh

# Run the Python tests
python3 simple_s3_test.py
python3 test_s3.py
```

### Implementation Details

The S3 integration is implemented through the `S3StorageService` class in `app/services/storage_service.py`. This service provides methods for:

- Uploading files (`upload_file`)
- Uploading text content (`upload_text_file`)
- Generating presigned URLs for secure access (`get_file_url`)
- Deleting files (`delete_file`)

The application automatically switches between local storage and S3 storage based on the `USE_S3_STORAGE` environment variable.

### Document Processing Flow with S3

When S3 storage is enabled:

1. Documents uploaded through the API are processed normally
2. Instead of saving files to the local filesystem, they are uploaded to S3
3. File paths in the database reference the S3 object keys
4. When a file is requested, a presigned URL is generated for secure access
5. The user is redirected to the presigned URL to download the file

### Security Considerations

- The application uses presigned URLs with a limited expiration time (1 hour by default)
- URLs are signed using HMAC with the application's secret key
- Access control is enforced at both the application and S3 levels
- File uploads use a predictable path structure: `uploads/{user_id}/{timestamp}_{filename}`

## Understand FIRST
Why am I getting this error? I don't want solutions, I want to thoroughly understand the problem and look at the entire codebase and readme files to understand WHY this is the problem and dig deep to understand the ROOT problem and not move on until we FULLY comprehend the CORE issue.

## Create Log Files for Feedback
Requirements:

A separate log file must be created for each core functionality (e.g., starting services, placing orders, verifying responses, etc.).

Each log file should:

Include timestamps

Clearly label the section/function being executed

Log all standard output and error output

The script should create a main log directory (e.g., logs/YYYY-MM-DD_HH-MM-SS/) for each run and save all component logs inside it.

If any part fails, the script should continue running remaining steps but clearly mark failures in the logs.