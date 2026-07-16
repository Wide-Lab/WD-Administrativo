from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.unit_of_work import SQLAlchemyUnitOfWork
from src.modules.auth.adapters.db.repository import UserRepository


class AuthUnitOfWork(SQLAlchemyUnitOfWork):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        Inicializa a unidade de trabalho de autenticação.

        Args:
            session (AsyncSession):
                Sessão do banco de dados.
        """

        super().__init__(session=session)
        self._users: UserRepository | None = None

    @property
    def users(self) -> UserRepository:
        """Repositório de usuários."""
        if self._users is None:
            raise RuntimeError("Repositório de usuários não inicializado.")
        return self._users

    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self._users = UserRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        self._users = None
