from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.unit_of_work import SQLAlchemyUnitOfWork
from src.core.tenancy import OrganizationId
from src.modules.frota.adapters.db.repository import (
    DriverRepository,
    VehicleRepository,
    VehicleUsageRepository,
)


class FrotaUnitOfWork(SQLAlchemyUnitOfWork):
    """A unit of work da frota.

    Diferente da `AccessUnitOfWork`, ela recebe a **organização ativa** e a repassa aos três
    repositórios: eles são tenant-scoped, e nascem amarrados a ela. O `organization_id` vem de
    `current_organization` — nunca do corpo da requisição."""

    def __init__(self, session: AsyncSession, organization_id: OrganizationId) -> None:
        super().__init__(session=session)
        self._organization_id = organization_id
        self._vehicles: VehicleRepository | None = None
        self._drivers: DriverRepository | None = None
        self._usages: VehicleUsageRepository | None = None

    @property
    def vehicles(self) -> VehicleRepository:
        if self._vehicles is None:
            raise RuntimeError("Repositório de veículos não inicializado.")
        return self._vehicles

    @property
    def drivers(self) -> DriverRepository:
        if self._drivers is None:
            raise RuntimeError("Repositório de condutores não inicializado.")
        return self._drivers

    @property
    def usages(self) -> VehicleUsageRepository:
        if self._usages is None:
            raise RuntimeError("Repositório de usos não inicializado.")
        return self._usages

    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self._vehicles = VehicleRepository(self._session, self._organization_id)
        self._drivers = DriverRepository(self._session, self._organization_id)
        self._usages = VehicleUsageRepository(self._session, self._organization_id)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        self._vehicles = None
        self._drivers = None
        self._usages = None
