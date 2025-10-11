from sqlalchemy import create_engine, inspect
from app.core.config import settings
from app.db.models import User
from app.db.base import Base

def view_database():
    # Create engine
    engine = create_engine(settings.get_database_url())
    
    # Get inspector
    inspector = inspect(engine)
    
    # Get all tables
    tables = inspector.get_table_names()
    print("\nDatabase Tables:")
    print("===============")
    for table in tables:
        print(f"- {table}")
        
    # View Users table
    print("\nUsers:")
    print("======")
    with engine.connect() as connection:
        result = connection.execute("SELECT id, email, created_at FROM users")
        for row in result:
            print(f"ID: {row[0]}, Email: {row[1]}, Created: {row[2]}")

if __name__ == "__main__":
    view_database()