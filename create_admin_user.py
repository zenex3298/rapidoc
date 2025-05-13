import os
import sys
from sqlalchemy.orm import Session
from passlib.context import CryptContext

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the application modules
from app.core.database import get_db
from app.models.user import User

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin_user(db: Session, username: str, email: str, password: str):
    """Create an admin user in the database."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        print(f"User with email {email} already exists.")
        return

    # Create new admin user
    hashed_password = pwd_context.hash(password)
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    print(f"Admin user created successfully. Username: {username}, Email: {email}")
    return db_user

def main():
    """Main function to create an admin user."""
    username = "admin"
    email = "admin@example.com"
    password = "admin123"
    
    # Get database session
    db = next(get_db())
    
    try:
        create_admin_user(db, username, email, password)
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()