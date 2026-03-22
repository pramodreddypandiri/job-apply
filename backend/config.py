from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str = ""

    # Claude
    anthropic_api_key: str

    # Tavily
    tavily_api_key: str = ""

    # Gmail OAuth
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/auth/gmail/callback"

    # GitHub
    github_token: str = ""

    # Browser
    chrome_debug_port: int = 9222

    # Redis
    redis_url: str = "redis://localhost:6379"

    # App
    secret_key: str = "change-me-in-production"
    environment: str = "development"

    # Sentry
    sentry_dsn: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
