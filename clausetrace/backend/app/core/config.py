"""
ClauseTrace Application Configuration.
Loads environment variables from .env using Pydantic Settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ClauseTrace"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # AI Integration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Local Document Storage
    STORAGE_LOCAL_DIR: str = "./storage/contracts"

    # Mock user IDs for demo (Analyst vs Reviewer)
    DEMO_ANALYST_ID: str = "00000000-0000-0000-0000-000000000001"
    DEMO_REVIEWER_ID: str = "00000000-0000-0000-0000-000000000002"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_normalized_database_url(self) -> str:
        """Ensures asyncpg dialect prefix is present for SQLAlchemy."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    def ensure_storage_dir(self) -> Path:
        """Ensures local storage directory exists."""
        storage_path = Path(self.STORAGE_LOCAL_DIR)
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path


settings = Settings()
settings.ensure_storage_dir()

