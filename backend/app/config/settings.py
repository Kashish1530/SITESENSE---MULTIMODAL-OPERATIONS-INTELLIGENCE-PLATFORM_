from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL
import json


class Settings(BaseSettings):
    """Application Settings loaded from environment variables and .env file."""

    # Project metadata
    PROJECT_NAME: str = Field(
        default="SiteSense - Multimodal Operations Intelligence Platform",
        description="Name of the application",
    )
    VERSION: str = Field(default="1.0.0", description="API Version")
    DESCRIPTION: str = Field(
        default="Integration and orchestration backend layer for SiteSense multimodal system.",
        description="API Description for OpenAPI docs",
    )
    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DEBUG: bool = Field(default=True, description="Debug mode flag")

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    API_V1_PREFIX: str = Field(default="/api/v1", description="URL prefix for V1 API")

    # Security & Auth (Component 3)
    SECRET_KEY: str = Field(
        default="sitesense-development-secret-key-change-in-production-use",
        description="Secret key for JWT and encryption",
    )
    ALGORITHM: str = Field(default="HS256", description="Token signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # Database Configuration (Component 2 - Supports SQLite, PostgreSQL, and Neon Serverless)
    DATABASE_URL: str = Field(
        default="sqlite:///./sitesense.db",
        description="Database connection URL (Neon PostgreSQL in production or SQLite in dev)",
    )

    # Existing project database variables. DATABASE_URL takes priority when supplied.
    DB_HOST: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = Field(default=None, repr=False, exclude=True)
    DB_PORT: Optional[int] = None

    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(
        default=20, description="Database connection pool max overflow"
    )
    DB_POOL_PRE_PING: bool = Field(
        default=True, description="Pre-ping database connections before checkout (essential for Neon serverless)"
    )

    # CORS configuration
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:4173",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5175",
            "http://127.0.0.1:5176",
            "http://127.0.0.1:4173",
            "http://127.0.0.1:8000",
        ],
        description="Allowed CORS origins",
    )

    # File and media storage (Component 5 / M1 & M2)
    MEDIA_STORAGE_PATH: str = Field(
        default="./media_storage", description="Local filesystem path for media storage"
    )
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=100, description="Maximum single file upload size in MB"
    )
    STORAGE_BACKEND: str = Field(
        default="minio", description="Storage backend: local | minio"
    )
    MINIO_ENDPOINT: str = Field(
        default="localhost:9000", description="MinIO host:port"
    )
    MINIO_ACCESS_KEY: str = Field(
        default="minioadmin", description="MinIO access key"
    )
    MINIO_SECRET_KEY: str = Field(
        default="minioadmin", description="MinIO secret key"
    )
    MINIO_BUCKET_NAME: str = Field(
        default="sitesense-media", description="MinIO media bucket name"
    )
    MINIO_SECURE: bool = Field(
        default=False, description="Use SSL/TLS for MinIO"
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Application logging level")

    # Optional AI / Model Provider Keys (Component 7 / M2, M3, M4)
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    VECTOR_STORE_DIR: str = Field(default="./vector_store", description="Vector database path")
    YOLO_MODEL_PATH: str = Field(default="./app/weights/best_3.pt", description="YOLO weights file")

    # Resolve the project-root .env regardless of the current working directory.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def build_database_url_from_existing_env(cls, values):
        """Use DB_* credentials when DATABASE_URL is not explicitly supplied."""
        if not isinstance(values, dict):
            return values

        explicit_url = values.get("DATABASE_URL")
        if explicit_url:
            return values

        host = values.get("DB_HOST")
        database = values.get("DB_NAME")
        username = values.get("DB_USER")
        password = values.get("DB_PASSWORD")
        port = values.get("DB_PORT") or 5432

        if all([host, database, username, password]):
            url = URL.create(
                drivername="postgresql+psycopg2",
                username=username,
                password=password,
                host=host,
                port=int(port),
                database=database,
                query={"sslmode": "require"},
            )
            values["DATABASE_URL"] = url.render_as_string(hide_password=False)

        return values

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Normalize database URL for SQLAlchemy compatibility (especially Neon and Heroku strings)."""
        if isinstance(v, str):
            v = v.strip()
            # Convert legacy postgres:// prefix to postgresql+psycopg2://
            if v.startswith("postgres://"):
                v = "postgresql+psycopg2://" + v[len("postgres://"):]
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                v = "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def is_sqlite(self) -> bool:
        """Check if database is SQLite."""
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def database_connect_args(self) -> dict:
        """Special connect args for database engine."""
        if self.is_sqlite:
            return {"check_same_thread": False}
        return {}


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
