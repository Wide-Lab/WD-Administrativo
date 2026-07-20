"""Os schemas de request/response da frota.

**A `PageResponse` daqui é uma cópia da que mora em `access/adapters/http/schemas.py`**, e a
duplicação é forçada pela fronteira: um app de negócio não importa `access`, e promovê-la ao
`core` mudaria `src/core` — que o critério 1 da spec proíbe explicitamente. As duas são o mesmo
envelope sobre a mesma `Page` do `core`. Ver `Como ficou` da spec 10."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from src.core.pagination.params import Page
from src.modules.frota.domain.entities import (
    Driver,
    DriverStatus,
    Vehicle,
    VehicleStatus,
    VehicleUsage,
)
from src.modules.frota.domain.rules import MileageGroup, MileageGroupBy, MileageSummary


class PageResponse[ItemT](BaseModel):
    """A `Page` do `core` traduzida pra resposta da API — ver o docstring do módulo."""

    items: list[ItemT]
    total: int
    page: int
    page_size: int

    @classmethod
    def of[EntityT](cls, page: Page[EntityT], items: list[ItemT]) -> PageResponse[ItemT]:
        return cls(
            items=items,
            total=page.total,
            page=page.page,
            page_size=page.page_size,
        )


class CreateVehicleRequest(BaseModel):
    plate: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    initial_odometer: int = Field(ge=0)
    model_year: int | None = None
    status: VehicleStatus = VehicleStatus.ACTIVE


class UpdateVehicleRequest(BaseModel):
    """Todos opcionais, mas ao menos um é exigido — o use case recusa o corpo vazio com 422."""

    plate: str | None = Field(default=None, min_length=1)
    brand: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    initial_odometer: int | None = Field(default=None, ge=0)
    model_year: int | None = None
    status: VehicleStatus | None = None


class VehicleResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    plate: str
    brand: str
    model: str
    model_year: int | None
    initial_odometer: int
    status: VehicleStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Vehicle) -> VehicleResponse:
        return cls(
            id=entity.id,
            organization_id=entity.organization_id,
            plate=entity.plate,
            brand=entity.brand,
            model=entity.model,
            model_year=entity.model_year,
            initial_odometer=entity.initial_odometer,
            status=entity.status,
            created_at=entity.created_at,
        )


class CreateDriverRequest(BaseModel):
    name: str = Field(min_length=1)
    user_id: uuid.UUID | None = None
    """O vínculo opcional com quem tem login. Quem o tem passa a poder lançar a própria viagem."""

    license_number: str | None = None
    license_category: str | None = None
    license_expires_at: date | None = None
    status: DriverStatus = DriverStatus.ACTIVE


class UpdateDriverRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    user_id: uuid.UUID | None = None
    license_number: str | None = None
    license_category: str | None = None
    license_expires_at: date | None = None
    status: DriverStatus | None = None


class DriverResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    user_id: uuid.UUID | None
    license_number: str | None
    license_category: str | None
    license_expires_at: date | None
    status: DriverStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Driver) -> DriverResponse:
        return cls(
            id=entity.id,
            organization_id=entity.organization_id,
            name=entity.name,
            user_id=entity.user_id,
            license_number=entity.license_number,
            license_category=entity.license_category,
            license_expires_at=entity.license_expires_at,
            status=entity.status,
            created_at=entity.created_at,
        )


class CreateUsageRequest(BaseModel):
    """O lançamento de uma viagem.

    `started_at` e `ended_at` são **digitados** — não há campo que o relógio do servidor preencha,
    e não existe rota "iniciar viagem agora". `driver_id` omitido significa "eu"; ver o docstring
    de `CreateUsageCommand`."""

    vehicle_id: uuid.UUID
    started_at: datetime
    start_odometer: int = Field(ge=0)
    driver_id: uuid.UUID | None = None
    ended_at: datetime | None = None
    end_odometer: int | None = Field(default=None, ge=0)
    purpose: str | None = None
    notes: str | None = None


class UpdateUsageRequest(BaseModel):
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    start_odometer: int | None = Field(default=None, ge=0)
    end_odometer: int | None = Field(default=None, ge=0)
    purpose: str | None = None
    notes: str | None = None


class CloseUsageRequest(BaseModel):
    """Os dois campos **juntos** — é o que a rota própria de encerrar existe pra garantir, e o
    `ck_vehicle_usages_closed_together` o impõe no banco."""

    ended_at: datetime
    end_odometer: int = Field(ge=0)


class UsageResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    start_odometer: int
    end_odometer: int | None
    distance: int | None
    """Os quilômetros rodados, ou `null` se a viagem está aberta. Derivado, não coluna."""

    purpose: str | None
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: VehicleUsage) -> UsageResponse:
        return cls(
            id=entity.id,
            organization_id=entity.organization_id,
            vehicle_id=entity.vehicle_id,
            driver_id=entity.driver_id,
            started_at=entity.started_at,
            ended_at=entity.ended_at,
            start_odometer=entity.start_odometer,
            end_odometer=entity.end_odometer,
            distance=entity.distance,
            purpose=entity.purpose,
            notes=entity.notes,
            created_by=entity.created_by,
            created_at=entity.created_at,
        )


class MileageGroupResponse(BaseModel):
    id: uuid.UUID
    label: str
    total_km: int
    closed_usages: int
    open_usages: int
    """Nunca somados como zero km — ver `MileageGroup.open_usages`."""

    @classmethod
    def from_entity(cls, entity: MileageGroup) -> MileageGroupResponse:
        return cls(
            id=entity.id,
            label=entity.label,
            total_km=entity.total_km,
            closed_usages=entity.closed_usages,
            open_usages=entity.open_usages,
        )


class MileageReportResponse(BaseModel):
    group_by: MileageGroupBy
    groups: list[MileageGroupResponse]

    @classmethod
    def from_result(cls, result: MileageSummary) -> MileageReportResponse:
        return cls(
            group_by=result.group_by,
            groups=[MileageGroupResponse.from_entity(item) for item in result.groups],
        )
