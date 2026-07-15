import uuid
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from src.core.pagination.params import Page, PageParams
from src.core.types import BaseCreateCommand, BaseUpdateCommand


class UnitOfWork(ABC):
    """Unidade de trabalho: agrupa operações numa transação. `commit` é explícito; sair do
    contexto sem commit descarta a transação."""

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...


class Repository[
    EntityT,
    FiltersT,
    CreateCommandT: BaseCreateCommand,
    UpdateCommandT: BaseUpdateCommand,
](ABC):
    """Contrato de repositório: CRUD + paginação sobre uma entidade de domínio."""

    @abstractmethod
    async def get_by_id_or_none(self, id_: uuid.UUID) -> EntityT | None: ...

    @abstractmethod
    async def get_by_id(self, id_: uuid.UUID) -> EntityT: ...

    @abstractmethod
    async def create(self, create_command: CreateCommandT) -> EntityT: ...

    @abstractmethod
    async def update(self, id_: uuid.UUID, update_command: UpdateCommandT) -> EntityT: ...

    @abstractmethod
    async def delete(self, id_: uuid.UUID) -> None: ...

    @abstractmethod
    async def paginate(
        self, page_params: PageParams, filters: FiltersT | None = None
    ) -> Page[EntityT]: ...
