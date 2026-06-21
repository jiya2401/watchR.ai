from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # Gemini
    gemini_api_key: str
    gemini_fast_model: str = "gemini-2.5-flash-preview-05-20"
    gemini_smart_model: str = "gemini-2.5-pro-preview-05-06"
    gemini_embedding_model: str = "models/text-embedding-004"
    gemini_rpm_fast: int = 10
    gemini_rpm_smart: int = 2
    embed_batch_size: int = 20

    # MongoDB
    mongo_uri: str
    mongo_db: str

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_cache_db: str
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # ChromaDB
    chroma_persist_dir: str = "/data/chroma" 

    # App
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_prod(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached — reads .env once per process."""
    return Settings()
