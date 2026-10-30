from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env."""

    app_name: str = "Campus Intelligence & Placement Assistant API"
    app_version: str = "0.1.0"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    auto_create_tables: bool = True

    # Local PostgreSQL settings. Keep real credentials in .env, never in Git.
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("change-me")
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "Campus_Intelligence"
    database_url: SecretStr | None = None

    # Authentication mode: development is for local use only; production uses Firebase.
    auth_mode: str = "development"
    firebase_project_id: str | None = None
    firebase_service_account_json: SecretStr | None = None

    # AI provider. AI-dependent routes return HTTP 503 until a key is configured.
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.8-flash"
    # Optional second model tried automatically when the primary model's quota is exhausted.
    gemini_fallback_model: str | None = None
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_embedding_dimensions: int = 768

    # File handling.
    storage_dir: Path = BACKEND_DIR / "storage"
    max_upload_mb: int = 15
    max_pdf_pages: int = 300
    max_document_chunks_for_retrieval: int = 600

    # CORS is comma-separated in .env, e.g. http://localhost:5173,http://127.0.0.1:5173
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("auth_mode")
    @classmethod
    def normalize_auth_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "firebase"}:
            raise ValueError("AUTH_MODE must be either 'development' or 'firebase'.")
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def gemini_key_value(self) -> str | None:
        return self.gemini_api_key.get_secret_value() if self.gemini_api_key else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
