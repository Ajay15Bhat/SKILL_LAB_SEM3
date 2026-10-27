"""
ClauseTrace Application Configuration.
Loads settings from environment variables or .env file with graceful defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ClauseTrace"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database: Supabase PostgreSQL (asyncpg) or local SQLite fallback
    # Default to sqlite for seamless zero-dependency out-of-the-box local testing
    DATABASE_URL: str = "sqlite+aiosqlite:///./clausetrace.db"

    # Supabase optional credentials
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Google Gemini API key (optional for enhanced semantic reasoning)
    GEMINI_API_KEY: Optional[str] = None

    # Hugging Face API key (optional)
    HUGGINGFACE_API_KEY: Optional[str] = None

    # Private document storage path
    STORAGE_LOCAL_DIR: str = "./storage/contracts"

    # Max upload file size in bytes (e.g. 50 MB)
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024

    # CORS origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Normalize Postgres URLs to asyncpg
if settings.DATABASE_URL.startswith("postgresql://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
