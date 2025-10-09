"""Pydantic settings for Web Notes API.

Behavior:
- Reads ENV_FILE environment variable at import time and uses it as the env file path.
- If ENV_FILE is not set, falls back to ".env".
- ALLOWED_ORIGINS accepts a JSON array string (e.g. '["http://localhost:3000"]') or a Python list.
Usage:
    from backend.app.config import settings
    db_url = settings.DATABASE_URL
"""

from __future__ import annotations

import os
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./notes.db"

    # JWT / Auth
    JWT_SECRET_KEY: str = "change-me"  # override in env for production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Server
    HOST: str = "localhost"
    PORT: int = 8000
    DEBUG: bool = True

    # CORS - Accepts JSON array string or Python list
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "chrome-extension://*"]
    )

    # CORS regex pattern for dynamic origin matching
    ALLOWED_ORIGINS_REGEX: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5

    class Config:
        # Use ENV_FILE env var to choose which .env file to load
        env_file = os.getenv("ENV_FILE", ".env")
        env_file_encoding = "utf-8"
        # allow case-insensitive env names
        case_sensitive = False


# singleton settings instance
settings = Settings()
