#!/usr/bin/env python3
"""
Database management script for RapiDoc application
"""
import argparse
import logging
import sys
from app.core.database import engine
from app.scripts.db.reset_database import reset_database, reset_migrations
from app.scripts.db.verify_database import verify_database

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_parser():
    """Create argument parser for CLI"""
    parser = argparse.ArgumentParser(description='Database Management for RapiDoc')
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset database schema')
    reset_parser.add_argument('--with-migrations', action='store_true', 
                             help='Also reset Alembic migrations')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify database schema')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Display database information')
    
    return parser

def display_db_info():
    """Display information about the database"""
    from sqlalchemy import inspect, text
    
    # Check if tables exist
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    logger.info("Database information:")
    logger.info(f"Database URL: {engine.url}")
    logger.info(f"Tables: {', '.join(tables)}")
    
    # Check if migration table exists
    if "alembic_version" in tables:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            logger.info(f"Alembic version: {version}")
    
    # Count rows in each table
    with engine.connect() as conn:
        for table in tables:
            if table != 'alembic_version':
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"Table '{table}': {count} rows")
    
    return True

def main():
    """Main function to run the CLI"""
    parser = create_parser()
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute the command
    if args.command == 'reset':
        # Reset database schema
        success = reset_database()
        
        # Reset migrations if requested
        if args.with_migrations and success:
            success = reset_migrations()
        
        return 0 if success else 1
    
    elif args.command == 'verify':
        # Verify database
        success = verify_database()
        return 0 if success else 1
    
    elif args.command == 'info':
        # Display database info
        success = display_db_info()
        return 0 if success else 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())