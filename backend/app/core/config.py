from __future__ import annotations
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    database_url: str = f"sqlite:///{BASE_DIR / 'auta.db'}"
    secret_key: str = "auta-dev-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    upload_dir: str = str(BASE_DIR / "uploads")
    # Grok (xAI) — API compatible OpenAI (/chat/completions)
    grok_api_key: str = ""
    grok_base_url: str = "https://api.x.ai/v1"
    grok_model: str = "grok-3-mini"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Sécurité
    allow_open_registration: bool = False

    # File d'extraction (optionnel)
    redis_url: str = ""

    # Stockage S3 / R2 (optionnel — sinon disque local)
    s3_bucket: str = ""
    s3_region: str = "eu-west-3"
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_prefix: str = "auta"

    # Stockage Supabase (prioritaire si configuré)
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket: str = "auta"

    # Email SMTP (optionnel)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True

    # SMS stub
    sms_provider_url: str = ""
    sms_api_key: str = ""

    # Monitoring
    sentry_dsn: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def s3_enabled(self) -> bool:
        return bool(self.s3_bucket and self.s3_access_key and self.s3_secret_key)

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def remote_storage_enabled(self) -> bool:
        return self.supabase_enabled or self.s3_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
