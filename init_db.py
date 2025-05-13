"""
Database initialization script for Heroku
"""

import os
import sys
from sqlalchemy import create_engine, text
from app.core.database import Base, engine
from app.models.user import User  # Import all models
from app.models.document import Document
from app.models.activity_log import ActivityLog

def init_db():
    """Initialize the database by creating all tables"""
    print("Creating database tables...")
    
    # Explicitly import and register all models
    print(f"Preparing to create tables for models: User, Document, ActivityLog")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    
    # Verify tables were created
    try:
        conn = engine.connect()
        # List all tables
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
        print(f"Created tables: {', '.join([t[0] for t in tables])}")
        
        # Specifically check for our model tables
        model_tables = ['users', 'documents', 'activity_logs']
        for table in model_tables:
            exists = conn.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")).scalar()
            if exists:
                print(f"✓ Table '{table}' exists")
            else:
                print(f"✗ Table '{table}' does not exist")
        
        conn.close()
    except Exception as e:
        print(f"Error verifying tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = init_db()
    if success:
        print("Database initialization completed successfully.")
        sys.exit(0)
    else:
        print("Database initialization failed.")
        sys.exit(1)