"""Os comandos que as rotas da frota entregam aos use cases.

Nenhum deles carrega `organization_id`: a organização é a do path, resolvida por
`current_organization`, e o repositório tenant-scoped a carimba. Aceitá-la no corpo abriria
gravar em nome de outra Empresa."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from src.modules.frota.domain.entities import DriverStatus, VehicleStatus

__all__ = [
    "CloseUsageCommand",
    "CreateDriverCommand",
    "CreateUsageCommand",
    "CreateVehicleCommand",
    "UpdateDriverCommand",
    "UpdateUsageCommand",
    "UpdateVehicleCommand",
]


@dataclass(frozen=True, slots=True)
class CreateVehicleCommand:
    plate: str
    brand: str
    model: str
    initial_odometer: int
    model_year: int | None = None
    status: VehicleStatus = VehicleStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateVehicleCommand:
    plate: str | None = None
    brand: str | None = None
    model: str | None = None
    model_year: int | None = None
    initial_odometer: int | None = None
    status: VehicleStatus | None = None


@dataclass(frozen=True, slots=True)
class CreateDriverCommand:
    name: str
    user_id: uuid.UUID | None = None
    license_number: str | None = None
    license_category: str | None = None
    license_expires_at: date | None = None
    status: DriverStatus = DriverStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateDriverCommand:
    name: str | None = None
    user_id: uuid.UUID | None = None
    license_number: str | None = None
    license_category: str | None = None
    license_expires_at: date | None = None
    status: DriverStatus | None = None


@dataclass(frozen=True, slots=True)
class CreateUsageCommand:
    """O lançamento de uma viagem.

    **`driver_id` é opcional, e omiti-lo significa "eu"** — resolvido pelo condutor vinculado ao
    `user_id` de quem chama. Isso não estava na spec e foi necessário pra o fluxo dela fechar: um
    `collaborator` não tem `frota.drivers.read`, então ele **não tem como descobrir o próprio
    `driver_id`** pra mandá-lo. Exigir o campo tornaria impossível na prática o único gesto que a
    spec dá a ele. Mandá-lo continua valendo, e mandar o de outro condutor com só `write_own`
    segue sendo 403 — o critério 4 não muda. Ver `Como ficou`."""

    vehicle_id: uuid.UUID
    started_at: datetime
    start_odometer: int
    driver_id: uuid.UUID | None = None
    ended_at: datetime | None = None
    end_odometer: int | None = None
    purpose: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateUsageCommand:
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    start_odometer: int | None = None
    end_odometer: int | None = None
    purpose: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class CloseUsageCommand:
    """Encerrar recebe os dois campos **juntos**, e é por isso que é rota própria e não um
    `PATCH`: a transição tem validação própria (o `ck_vehicle_usages_closed_together`), e
    encerrar uma viagem já encerrada é 409 enquanto corrigir uma encerrada é legítimo. Espremer
    as duas num `PATCH` faria "fechar" e "corrigir" indistinguíveis no log e na permissão."""

    ended_at: datetime
    end_odometer: int
