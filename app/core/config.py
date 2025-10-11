import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "TenderBridge"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgres://postgres:password@db:5432/tenderbridge")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

    def get_database_url(self):
        url = self.DATABASE_URL
        # Fix for SQLAlchemy compatibility (if using 'postgres://' instead of 'postgresql+psycopg2://')
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        return url

settings = Settings()
