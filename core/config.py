import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # ⚠️ CRITICAL: In production, SECRET_KEY MUST be set via environment variable
    SECRET_KEY = os.getenv("SECRET_KEY", None)
    if not SECRET_KEY:
        raise ValueError(
            "ERROR: SECRET_KEY environment variable is not set. "
            "Set a strong, random SECRET_KEY for security. "
            "Example: openssl rand -hex 32"
        )
    
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Database configuration validation
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    if ENVIRONMENT not in ("development", "production", "testing"):
        raise ValueError(f"Invalid ENVIRONMENT: {ENVIRONMENT}")

settings = Settings()

