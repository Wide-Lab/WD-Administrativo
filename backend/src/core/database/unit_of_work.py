import logging
from types import TracebackType
from typing import Self

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.ports import UnitOfWork
from src.core.exceptions import ConflictError, PersistenceError

logger = logging.getLogger(__name__)


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa a unidade de trabalho.

        Args:
            session (AsyncSession):
                Sessão do banco de dados.
        """

        self._session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Ao sair do contexto: se houve exceção, desfaz; sempre fecha a sessão. O `commit`
        é explícito — sair sem chamar `commit()` descarta a transação."""

        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        """Efetiva a transação. Traduz violação de integridade em `ConflictError` e qualquer
        outra falha em `PersistenceError`, desfazendo a transação antes de propagar."""

        try:
            await self._session.commit()
        except IntegrityError as exc:
            logger.warning("Violação de integridade ao efetivar a transação.", exc_info=True)
            await self.rollback()
            raise ConflictError("Violação de integridade ao efetivar a transação.") from exc
        except Exception as exc:
            logger.error("Falha ao efetivar a transação.", exc_info=True)
            await self.rollback()
            raise PersistenceError("Falha ao efetivar a transação.") from exc

    async def rollback(self) -> None:
        """Desfaz a transação corrente."""

        await self._session.rollback()
