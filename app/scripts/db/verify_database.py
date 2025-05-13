import logging
from sqlalchemy import inspect, text
from app.core.database import engine, get_db
from app.models.user import User

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_database():
    """Verify database schema and create a test user"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Tables in database: {', '.join(tables)}")
        
        # Check if migration table exists and has the expected revision
        with engine.connect() as conn:
            if "alembic_version" in tables:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                logger.info(f"Current alembic version: {version}")
            else:
                logger.warning("No alembic_version table found!")
        
        # Try to create a test user
        logger.info("Creating test user...")
        # Get hash from the auth service to ensure compatibility
        from app.services.auth_service import get_password_hash
        test_user = User(
            email="admin@example.com",
            username="admin",
            hashed_password=get_password_hash("password"),
            is_active=True,
            is_admin=True
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        logger.info(f"Test user created with ID: {test_user.id}")
        
        # Query to verify
        users = db.query(User).all()
        for user in users:
            logger.info(f"User in database: {user}")
        
        logger.info("Database verification successful!")
        return True
    
    except Exception as e:
        logger.error(f"Error verifying database: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    verify_database()