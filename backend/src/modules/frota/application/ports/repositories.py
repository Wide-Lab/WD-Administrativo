"""As portas de persistência da frota.

A `application` conhece **estes protocolos**, nunca `adapters`. É o que deixa um use case ser
lido (e trocado) sem saber que existe SQLAlchemy do outro lado."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from src.core.pagination.params import Page, PageParams
from src.modules.frota.application.dtos.filters import (
    DriverFilters,
    VehicleFilters,
    VehicleUsageFilters,
)
from src.modules.frota.domain.entities import (
    Driver,
    NewDriver,
    NewOdometerReading,
    NewVehicle,
    NewVehicleUsage,
    OdometerReading,
    UpdateDriver,
    UpdateVehicle,
    UpdateVehicleUsage,
    Vehicle,
    VehicleUsage,
)
from src.modules.frota.domain.rules import UsageForReport

__all__ = [
    "DriverRepositoryProtocol",
    "OdometerReadingRepositoryProtocol",
    "VehicleRepositoryProtocol",
    "VehicleUsageRepositoryProtocol",
]


class VehicleRepositoryProtocol(Protocol):
    async def get_by_id_or_none(self, id_: uuid.UUID) -> Vehicle | None: ...

    async def create(self, create_command: NewVehicle) -> Vehicle: ...

    async def update(self, id_: uuid.UUID, update_command: UpdateVehicle) -> Vehicle: ...

    async def paginate(
        self,
        page_params: PageParams,
        filters: VehicleFilters | None = None,
    ) -> Page[Vehicle]: ...

    async def labels(self) -> dict[uuid.UUID, str]: ...


class DriverRepositoryProtocol(Protocol):
    async def get_by_id_or_none(self, id_: uuid.UUID) -> Driver | None: ...

    async def get_by_user_id(self, user_id: uuid.UUID) -> Driver | None: ...

    async def create(self, create_command: NewDriver) -> Driver: ...

    async def update(self, id_: uuid.UUID, update_command: UpdateDriver) -> Driver: ...

    async def paginate(
        self,
        page_params: PageParams,
        filters: DriverFilters | None = None,
    ) -> Page[Driver]: ...

    async def labels(self) -> dict[uuid.UUID, str]: ...


class VehicleUsageRepositoryProtocol(Protocol):
    async def get_by_id_or_none(self, id_: uuid.UUID) -> VehicleUsage | None: ...

    async def create(self, create_command: NewVehicleUsage) -> VehicleUsage: ...

    async def update(
        self,
        id_: uuid.UUID,
        update_command: UpdateVehicleUsage,
    ) -> VehicleUsage: ...

    async def delete(self, id_: uuid.UUID) -> None: ...

    async def close_if_open(
        self,
        id_: uuid.UUID,
        ended_at: datetime,
        end_odometer: int,
        end_reading_id: uuid.UUID | None = None,
    ) -> bool: ...

    async def is_reading_referenced(self, reading_id: uuid.UUID) -> bool: ...

    async def paginate(
        self,
        page_params: PageParams,
        filters: VehicleUsageFilters | None = None,
    ) -> Page[VehicleUsage]: ...

    async def list_for_report(
        self,
        started_from: datetime,
        started_until: datetime,
    ) -> list[UsageForReport]: ...


class OdometerReadingRepositoryProtocol(Protocol):
    """Sem `update`: leitura é o que a máquina disse, e o que a máquina disse não se corrige."""

    async def get_by_id_or_none(self, id_: uuid.UUID) -> OdometerReading | None: ...

    async def create(self, create_command: NewOdometerReading) -> OdometerReading: ...

    async def count_by_user_since(self, user_id: uuid.UUID, since: datetime) -> int: ...

    async def list_orphans(
        self,
        older_than: datetime,
        limit: int,
    ) -> list[OdometerReading]: ...

    async def delete_many(self, ids: Sequence[uuid.UUID]) -> None: ...
