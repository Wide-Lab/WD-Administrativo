"""Os filtros das listagens da frota."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from src.modules.frota.domain.entities import DriverStatus, VehicleStatus

__all__ = [
    "DriverFilters",
    "OdometerReadingFilters",
    "VehicleFilters",
    "VehicleUsageFilters",
]


@dataclass(frozen=True, slots=True)
class VehicleFilters:
    status: VehicleStatus | None = None


@dataclass(frozen=True, slots=True)
class DriverFilters:
    status: DriverStatus | None = None


@dataclass(frozen=True, slots=True)
class OdometerReadingFilters:
    """Não há rota que liste leituras — e é decisão da spec 11: uma tela que lista fotos soltas é
    arquivo, não produto, e a foto aparece **na viagem**, que é onde ela significa alguma coisa.

    Isto existe porque o `TenantScopedRepository` do `core` é genérico sobre um tipo de filtro, e
    um repositório sem filtro nenhum não tem como se declarar."""

    vehicle_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class VehicleUsageFilters:
    """Os filtros de `GET /usos`.

    `driver_id` é o mesmo campo que o filtro `?condutor=` e que o **escopo** de quem só tem
    `write_own` — e isso é de propósito: uma rota só, e não duas, porque duplicá-la duplicaria
    paginação, filtros e ordenação pra mudar uma cláusula `WHERE`. Quem decide o valor num caso é
    o usuário; no outro, o guard."""

    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    started_from: datetime | None = None
    started_until: datetime | None = None
    only_open: bool = False
