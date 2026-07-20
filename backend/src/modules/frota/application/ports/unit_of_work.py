from types import TracebackType
from typing import Protocol, Self

from src.modules.frota.application.ports.repositories import (
    DriverRepositoryProtocol,
    VehicleRepositoryProtocol,
    VehicleUsageRepositoryProtocol,
)


class FrotaUnitOfWorkProtocol(Protocol):
    @property
    def vehicles(self) -> VehicleRepositoryProtocol: ...

    @property
    def drivers(self) -> DriverRepositoryProtocol: ...

    @property
    def usages(self) -> VehicleUsageRepositoryProtocol: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
