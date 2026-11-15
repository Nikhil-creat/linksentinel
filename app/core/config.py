"""Typed settings loaded from environment."""
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str
    ip_salt: str
    groq_api_key: str = ""
    gemini_api_key: str = ""
    rate_limit: int = 60
    inline_agents: bool = False  # True on hosts without a Celery worker (e.g. Render free)

    @field_validator("database_url")
    @classmethod
    def _asyncpg(cls, v: str) -> str:
        return v.replace("postgres://", "postgresql+asyncpg://", 1).replace("postgresql://", "postgresql+asyncpg://", 1)
    cors_origins: str = "http://localhost:8080"
    cors_regex: str = r"https://[a-z0-9-]+\.vercel\.app"

settings = Settings()  # type: ignore[call-arg]
