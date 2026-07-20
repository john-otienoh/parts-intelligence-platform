"""Application settings loaded from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str | None = None
    SECRET_KEY: str = "dev-secret-change-me"
    CORS_ORIGINS: str = "*"
    CACHE_TTL_SECONDS: int = 300

    class Config:
        env_file = ".env"


settings = Settings()
