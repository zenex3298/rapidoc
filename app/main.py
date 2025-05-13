from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from app.core.database import engine, Base
import uvicorn

# Set up logging for Heroku compatibility (primarily to stdout/stderr)
# Get log level from environment variable with INFO as default
log_level_name = os.environ.get('LOG_LEVEL', 'INFO')
log_level = getattr(logging, log_level_name.upper(), logging.INFO)

# In production (like Heroku), we'll primarily log to stdout/stderr
# In development, we'll also log to a file if the logs directory exists
handlers = [logging.StreamHandler()]

# Only add file logging in development environments where the directory exists
# or can be created (not on Heroku's ephemeral filesystem)
if os.environ.get('ENVIRONMENT', 'development') == 'development':
    try:
        os.makedirs('logs', exist_ok=True)
        handlers.append(logging.FileHandler('logs/app.log'))
    except Exception:
        # If we can't create or write to logs directory, just use stdout/stderr
        pass

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="RapidocsAI API",
    description="AI-powered document analysis, storage and management platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# Import and include routers
from app.routes import auth_router, users_router, documents_router, admin_router
from app.frontend import frontend_router, static_path
from fastapi.staticfiles import StaticFiles

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include API routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(documents_router)
app.include_router(admin_router)

# Include frontend router
app.include_router(frontend_router)

# API root endpoint is now handled by the frontend router
# This fallback is kept for direct API access
@app.get("/api")
async def api_root():
    """
    API root endpoint to verify the API is working
    """
    logger.info("API root endpoint accessed")
    return {"message": "Welcome to the RapidocsAI API. Visit /docs for API documentation."}

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    logger.info("Health check performed")
    return {"status": "healthy"}

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    # Check if we're in development or production environment
    is_production = os.environ.get('ENVIRONMENT', 'development') == 'production'
    
    # Create uploads directory in development or if it seems possible
    # (Heroku has an ephemeral filesystem that won't persist uploads between dynos)
    if not is_production:
        try:
            os.makedirs('uploads', exist_ok=True)
            logger.info("Created local uploads directory")
        except Exception as e:
            logger.warning(f"Could not create uploads directory: {e}")
    
    # Check for required configuration in production
    if is_production:
        logger.info("Running in production mode")
        # Check for S3 configuration which is required in production
        if os.environ.get('USE_S3_STORAGE', '').lower() != 'true':
            logger.warning("USE_S3_STORAGE not set to 'true' - uploads will fail on Heroku's ephemeral filesystem")
        
        required_vars = [
            'AWS_ACCESS_KEY_ID', 
            'AWS_SECRET_ACCESS_KEY', 
            'S3_BUCKET_NAME',
            'JWT_SECRET_KEY',
            'DATABASE_URL'
        ]
        
        for var in required_vars:
            if not os.environ.get(var):
                logger.warning(f"Required environment variable {var} is not set!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")
    # Additional cleanup tasks can be added here

if __name__ == "__main__":
    # Use PORT environment variable if available (for Heroku compatibility)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)