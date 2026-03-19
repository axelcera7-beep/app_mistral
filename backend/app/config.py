"""Application settings loaded from environment variables."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Resolve project root: 
# Local: backend/app/config.py → ../../..  → projet-mistral/
# Docker: /app/app/config.py → ../.. → /app/
_cur = Path(__file__).resolve().parent.parent
if (_cur / "app").exists() and (_cur / "frontend").exists():
    PROJECT_ROOT = _cur
else:
    PROJECT_ROOT = _cur.parent

ENV_FILE = PROJECT_ROOT / ".env"
DB_PATH = PROJECT_ROOT / "data" / "data.db"


class Settings(BaseSettings):
    """Configuration loaded from .env or environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
    )

    mistral_api_key: str
    secret_key: str = "dev-secret-change-me-in-production"
    database_url: str = f"sqlite:///{DB_PATH}"

    # Mistral model identifiers
    text_model: str = "mistral-small-latest"
    vision_model: str = "pixtral-12b-2409"
    voice_model: str = "voxtral-mini-latest"
    embed_model: str = "mistral-embed"

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # Adzuna API (Job Search — fallback)
    adzuna_app_id: Optional[str] = None
    adzuna_api_key: Optional[str] = None

    # JSearch API via RapidAPI (primary job search)
    jsearch_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Singleton accessor for application settings."""
    return Settings()
