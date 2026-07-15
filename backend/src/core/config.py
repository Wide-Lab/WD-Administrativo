from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = []


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()  # type: ignore[call-arg]
