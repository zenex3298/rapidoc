import os
import logging
import shutil
import subprocess
import sys
import time
from sqlalchemy import inspect, text
from app.core.database import engine, Base
from app.models.user import User
from app.models.document import Document
from app.models.activity_log import ActivityLog

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """Drop all tables and recreate them"""
    inspector = inspect(engine)
    
    # Get all table names
    tables = inspector.get_table_names()
    
    if tables:
        logger.info(f"Found tables: {', '.join(tables)}")
        logger.info("Dropping all tables...")
        
        # Drop alembic_version table first if it exists
        with engine.connect() as conn:
            if "alembic_version" in tables:
                conn.execute(text("DROP TABLE alembic_version"))
                conn.commit()
                logger.info("Dropped alembic_version table")
        
        # Drop all SQLAlchemy-managed tables
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")
    else:
        logger.info("No tables found in the database")
    
    # Recreate all tables
    logger.info("Recreating tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema recreated successfully")

def reset_migrations():
    """Reset alembic migrations"""
    logger.info("Resetting migrations...")
    
    # Create or clear the versions directory 
    versions_dir = os.path.join("alembic", "versions")
    if not os.path.exists(versions_dir):
        os.makedirs(versions_dir)
    else:
        # Back up existing migrations
        backup_dir = os.path.join("alembic", "versions_backup")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = time.strftime("%Y%m%d%H%M%S")
        for filename in os.listdir(versions_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                src_file = os.path.join(versions_dir, filename)
                dst_file = os.path.join(backup_dir, f"{timestamp}_{filename}")
                shutil.move(src_file, dst_file)
        
        logger.info("Existing migrations backed up")
    
    # Initialize new migration
    logger.info("Creating new initial migration...")
    try:
        # Create initial migration
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", "initial_schema"], 
                       check=True)
        
        # Apply the migration
        subprocess.run(["alembic", "upgrade", "head"], 
                       check=True)
        
        logger.info("New migration created and applied successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create/apply migration: {e}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    reset_migrations_flag = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "--with-migrations":
            reset_migrations_flag = True
    
    # Reset database schema
    reset_database()
    
    # Reset migrations if requested
    if reset_migrations_flag:
        reset_migrations()
    
    logger.info("Database reset complete!")