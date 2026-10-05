#!/usr/bin/env python3
"""
Initialize the PostgreSQL database with schema from models.
Run this after the database is created and connection is configured in .env
"""
import sys
import time
from sqlalchemy import create_engine, text
from app.db.models import Base
from app.core.config import get_settings

def init_database():
    settings = get_settings()

    if not settings.database_url:
        print("ERROR: DATABASE_URL not configured in .env")
        sys.exit(1)

    print(f"Connecting to database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'unknown'}")

    try:
        # Normalize the URL
        db_url = settings.database_url
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

        engine = create_engine(db_url, echo=False, future=True)

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")

        # Create all tables
        print("Creating tables...")
        Base.metadata.create_all(engine)
        print("✓ Tables created successfully")

        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            print(f"✓ Created tables: {', '.join(tables)}")

        print("\n✓ Database initialization complete!")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    init_database()
