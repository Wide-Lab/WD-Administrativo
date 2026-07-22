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

    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    """Onde os arquivos ficam. O default é `local` pelo mesmo motivo do `LoggingEmailSender`:
    `docker compose up db` continua subindo sem MinIO, e a suíte roda contra um diretório
    temporário sem serviço nenhum. Ver `core/storage/` (spec 11)."""

    STORAGE_LOCAL_DIR: str = "var/storage"
    """Raiz do `LocalDirectoryStorage`. Relativa ao diretório de onde o backend sobe."""

    S3_ENDPOINT_URL: str | None = None
    """O endpoint do MinIO (ou de qualquer S3-compatível). `None` fala com a AWS de verdade —
    e amarrar o produto à AWS contradiz vendê-lo self-hosted, então o endpoint é configurável."""

    S3_BUCKET: str = "administrativo"
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str = "us-east-1"

    OPENAI_API_KEY: str | None = None
    """Sem chave, a leitura de hodômetro **se abstém** em vez de estourar — o formulário segue
    utilizável e a pessoa digita. É o gêmeo do `LoggingEmailSender`: dev funciona fim a fim sem
    provedor configurado, e o que sai é honesto ("não consegui ler"), não um número inventado."""

    OPENAI_MODEL: str = "gpt-4o"
    """Gravado em cada leitura como `openai:<modelo>`, porque o motor vai trocar — e sem isso
    medir a qualidade da leitura em produção depois de uma troca misturaria as duas populações."""

    ODOMETER_READ_TIMEOUT_SECONDS: float = 15.0
    """Estourou, a leitura vira `valor: null` e a resposta é 201, não 504: um erro do fornecedor
    não pode bloquear o lançamento da viagem — o produto é o registro, a leitura é conveniência."""


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()  # type: ignore[call-arg]
