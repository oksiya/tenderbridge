import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "TenderBridge"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgres://postgres:password@db:5432/tenderbridge")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
    
    # Email Configuration (Phase 3)
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "smtp")  # smtp, sendgrid, console
    
    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "true").lower() == "true"
    
    # SendGrid Settings
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    
    # Email Sender Info
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "noreply@tenderbridge.com")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "TenderBridge")
    
    # Email Features
    EMAIL_TEST_MODE: bool = os.getenv("EMAIL_TEST_MODE", "false").lower() == "true"
    EMAIL_TEST_RECIPIENT: str = os.getenv("EMAIL_TEST_RECIPIENT", "")

    def get_database_url(self):
        url = self.DATABASE_URL
        # Fix for SQLAlchemy compatibility (if using 'postgres://' instead of 'postgresql+psycopg2://')
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        return url

settings = Settings()
