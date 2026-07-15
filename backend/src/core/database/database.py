import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.database.types import Engine

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Database:
    engine: Engine
    session_maker: async_sessionmaker[AsyncSession]

    def create_session(self) -> AsyncSession:
        """
        Cria e retorna uma nova sessão do banco de dados.

        Returns:
            AsyncSession:
                A nova sessão.
        """

        return self.session_maker()

    async def dispose_engine(self) -> None:
        """Fecha a conexão com o banco de dados."""

        await self.engine.dispose()
