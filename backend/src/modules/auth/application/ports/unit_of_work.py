from types import TracebackType
from typing import Protocol, Self

from src.modules.auth.application.ports.repositories import UserRepositoryProtocol


class AuthUnitOfWorkProtocol(Protocol):
    @property
    def users(self) -> UserRepositoryProtocol: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
