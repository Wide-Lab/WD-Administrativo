import logging
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import get_config
from src.core.database.database import Database

logger = logging.getLogger(__name__)


def create_engine() -> AsyncEngine:
    config = get_config()
    return create_async_engine(
        config.DATABASE_URL,
        echo=False,
        future=True,
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@lru_cache(maxsize=1)
def get_database() -> Database:
    """
    Cria e retorna uma instância do banco de dados.

    Returns:
        Database:
            Uma instância do banco de dados.
    """

    logger.info("Iniciando o engine do banco de dados e o sessionmaker...")
    engine = create_engine()
    return Database(
        engine=engine,
        session_maker=create_sessionmaker(engine),
    )
