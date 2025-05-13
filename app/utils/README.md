# Utility Tools

This directory contains utility modules that support various aspects of the application.

## Document Processor

The `document_processor.py` module provides utilities for processing documents, including:

- Text extraction from various document formats (PDF, DOCX, CSV, XLSX, TXT)
- Metadata extraction
- Document structure analysis
- Support for both local and S3 storage options

## Performance Logger

The `performance_logger.py` module provides performance monitoring capabilities:

- Detailed timing of operations
- Threshold monitoring for long-running operations
- Structured logging with session tracking
- Statistical aggregation of performance metrics

## Synchronous Processing Model

The application implements a robust Synchronous Processing Model with these key features:

### Timeout Handling

- Hard timeout limit set to 25 seconds (with 5-second buffer for Heroku's 30-second limit)
- Partial results returned for operations that exceed the time limit
- Early termination to prevent complete request failure
- Explicit timeout warnings in API responses

### Performance Monitoring

- Fine-grained timing of individual operations
- Detailed logs for operations exceeding thresholds
- Performance statistics for identifying bottlenecks
- Correlation IDs for tracking request flows

### Partial Processing

- Document status tracking (uploaded → processing → partially_processed/processed/error)
- Graceful degradation for large documents
- Clear status indicators to clients
- Special response headers for timeout and partial processing cases

### Error Handling

- Consistent error logging
- Detailed error information in logs
- Appropriate HTTP status codes for different error conditions
- User-friendly error messages

### OpenAI Integration Protection

- OpenAI call duration monitoring
- Truncation of large content before sending to API
- Fallback mechanisms for content that exceeds limits
- Result saving even for timed-out operations

### S3 Storage Integration

- Transparent handling of both local and S3 storage
- Secure presigned URLs for downloading from S3
- Cleanup of temporary files
- Appropriate content-type handling

## Usage

The core utility classes are designed to be used throughout the application. See the respective module docstrings for detailed usage information.

```python
# Example usage of performance logging
from app.utils.performance_logger import document_perf_logger

# Start timing an operation
timer_id = document_perf_logger.start_timer("operation_name", {
    "context": "details about the operation"
})

try:
    # Perform the operation
    result = some_operation()
    
    # Stop the timer with success status
    document_perf_logger.stop_timer(timer_id, {
        "status": "success",
        "result_size": len(result)
    })
    
except Exception as e:
    # Log operation failure
    document_perf_logger.log_operation_failed("operation_name", e)
    raise
```

## Extension Points

The utility modules are designed to be extended in the future:

1. **Background Processing**: The Synchronous Processing Model can be extended to use background processing for operations that exceed the time limit
2. **Distributed Tracing**: Performance logging can be extended to support distributed tracing systems like OpenTelemetry
3. **Advanced Rate Limiting**: Protection against API rate limits can be implemented
4. **Caching Layer**: Results caching can be added to avoid redundant processing