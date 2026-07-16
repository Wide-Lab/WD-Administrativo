from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
    )

    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = []

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"

    SESSION_COOKIE_NAME: str = "sessao"
    SESSION_TTL_HOURS: int = 12
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    INVITATION_TTL_DAYS: int = 7
    """Validade de um convite. O default de 7 dias é o da spec 06."""

    APP_BASE_URL: str = "http://localhost:3000"
    """Base do link de aceite que vai no e-mail do convite. É o frontend, não a API: o convite
    leva a pessoa pra tela de aceite (`frontend/06`), que é quem chama a API."""


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()  # type: ignore[call-arg]
