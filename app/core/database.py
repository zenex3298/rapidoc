from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

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
        handlers.append(logging.FileHandler('logs/database.log'))
    except Exception:
        # If we can't create or write to logs directory, just use stdout/stderr
        pass

# Configure logging if it hasn't been configured yet
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

logger = logging.getLogger(__name__)

# Conditionally load environment variables from .env file only if essential 
# environment variables are not already set
if not os.getenv("DATABASE_URL") and not os.getenv("JWT_SECRET_KEY"):
    try:
        logger.info("Attempting to load environment variables from .env file")
        load_dotenv()
    except Exception as e:
        logger.warning(f"Could not load .env file, using environment variables only: {e}")

# Database URL
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./app/utils/local_app.db"
)

# Handle Heroku's postgres:// format (they use postgres:// instead of postgresql://)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info("Converted Heroku DATABASE_URL format from postgres:// to postgresql://")

# Create engine with special arguments for SQLite to handle threading
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args=connect_args,
    echo=True  # Log all SQL queries
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def get_db():
    """
    Dependency function to get a database session.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        logger.info("Database session created")
        yield db
    finally:
        db.close()
        logger.info("Database session closed")