"""Os schemas de request/response da frota.

**A `PageResponse` daqui é uma cópia da que mora em `access/adapters/http/schemas.py`**, e a
duplicação é forçada pela fronteira: um app de negócio não importa `access`, e promovê-la ao
`core` mudaria `src/core` — que o critério 1 da spec proíbe explicitamente. As duas são o mesmo
envelope sobre a mesma `Page` do `core`. Ver `Como ficou` da spec 10."""

import uuid
from datetime import date, datetime

from pydantic import AwareDatetime, BaseModel, Field

from src.core.pagination.params import Page
from src.modules.frota.application.use_cases.read_odometer import OdometerReadingOutcome
from src.modules.frota.domain.entities import (
    Driver,
    DriverStatus,
    ReadingConfidence,
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
    current_odometer: int
    """O maior hodômetro que o sistema conhece deste carro — **derivado, nunca coluna**.

    É o que dá prior à leitura por foto (sem ele a resposta seria um número solto) e o que faz o
    campo de hodômetro de saída deixar de nascer vazio na tela. A `frontend/07` recusou derivá-lo
    de `GET /usos` no navegador pra não criar uma segunda contabilidade de quilometragem lá; aqui
    ele nasce onde devia."""

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
            current_odometer=entity.current_odometer,
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
    de `CreateUsageCommand`.

    **Os instantes exigem fuso** (`AwareDatetime`), e um sem fuso é 422 — nunca uma suposição. O
    servidor não tem como saber o fuso de quem digitou: assumir o dele gravaria a viagem das 8h
    de São Paulo às 8h UTC, três horas fora, sem erro nenhum aparecer. Pior, `started_at` ingênuo
    vinha explodindo em 500 na comparação com o `now()` do use case, que é aware. O cliente sabe o
    fuso de quem digita e é ele quem carimba o offset."""

    vehicle_id: uuid.UUID
    started_at: AwareDatetime
    start_odometer: int = Field(ge=0)
    driver_id: uuid.UUID | None = None
    ended_at: AwareDatetime | None = None
    end_odometer: int | None = Field(default=None, ge=0)
    purpose: str | None = None
    notes: str | None = None
    leitura_saida_id: uuid.UUID | None = None
    leitura_chegada_id: uuid.UUID | None = None
    """As fotos do painel, quando houve.

    **Em português, e o resto do corpo em inglês** — a inconsistência é da spec 11, que fixou
    estes dois nomes, e a `frontend/10` já codifica contra eles. Trocá-los aqui por
    `start_reading_id` deixaria o contrato divergente das duas specs de uma vez; o custo de
    seguí-los é a esquisitice de ler `vehicle_id` e `leitura_saida_id` no mesmo corpo. Ver
    `Como ficou`.

    Opcionais e assim permanecem: quem quiser digitar, digita. Um módulo que exigisse foto pra
    lançar viagem teria trocado uma folha de papel por uma catraca."""


class UpdateUsageRequest(BaseModel):
    """**Sem os campos de leitura, e é decisão.** Corrigir a foto de uma viagem já lançada é caso
    raro o bastante pra esperar quem peça — então não há rota, e a ausência aqui é o que garante
    isso sem um `if`."""
    vehicle_id: uuid.UUID | None = None
    driver_id: uuid.UUID | None = None
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None
    start_odometer: int | None = Field(default=None, ge=0)
    end_odometer: int | None = Field(default=None, ge=0)
    purpose: str | None = None
    notes: str | None = None


class CloseUsageRequest(BaseModel):
    """Os dois campos **juntos** — é o que a rota própria de encerrar existe pra garantir, e o
    `ck_vehicle_usages_closed_together` o impõe no banco.

    Com fuso, pelo mesmo motivo do `CreateUsageRequest`."""

    ended_at: AwareDatetime
    end_odometer: int = Field(ge=0)
    leitura_chegada_id: uuid.UUID | None = None
    """A foto de chegada, quando houve. Omiti-la **não apaga** uma que já estivesse lá."""


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
    start_reading_id: uuid.UUID | None
    end_reading_id: uuid.UUID | None
    """Se esta viagem tem foto de painel, e de qual lado.

    A spec 11 não os lista na resposta, mas a `frontend/10` precisa deles: o ícone de foto na
    lista de viagens só aparece quando há foto, e derivá-lo de uma chamada por linha seria N+1 na
    tela. São ids, não URLs — os bytes seguem saindo só por
    `GET /usos/{id}/hodometro/{saida|chegada}`, atrás dos guards."""

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
            start_reading_id=entity.start_reading_id,
            end_reading_id=entity.end_reading_id,
        )


_CONFIANCA = {
    ReadingConfidence.HIGH: "alta",
    ReadingConfidence.MEDIUM: "media",
    ReadingConfidence.LOW: "baixa",
}
"""O enum do banco (`high`/`medium`/`low`) traduzido pro rótulo da API.

A spec 11 escreve `"confianca": "alta"` e `"baixa"` na resposta; `"media"` vai **sem acento**,
como todo valor de enum que o frontend compara por igualdade neste projeto. As colunas seguem em
inglês, como manda o `CLAUDE.md` — quem fala português aqui é a borda HTTP."""


class OdometerReadingResponse(BaseModel):
    """O que a leitura por foto devolve — **201, sempre que a foto foi guardada**.

    Os nomes vêm em português porque a spec 11 os fixou assim e a `frontend/10` já os consome.

    Note o que **não** está aqui: o `note` do motor. Ele é material de diagnóstico nosso, vai pro
    log, e devolvê-lo daria à tela um texto de fornecedor pra exibir sem querer."""

    id: uuid.UUID
    valor: int | None
    """`null` quando o motor se absteve — e ainda assim **201 com a foto guardada**: a leitura
    aconteceu, o resultado é "não sei", e a foto serve de evidência do mesmo jeito."""

    confianca: str
    plausivel: bool
    """`ultimo_hodometro <= valor <= ultimo_hodometro + 2000`.

    **É sinal, nunca bloqueio**: `false` responde 201 com o número lido. A spec 10 já decidiu que
    divergência de hodômetro é aviso — travar faria o usuário inventar um número, que é pior que
    o buraco."""

    ultimo_hodometro: int
    delta: int | None

    @classmethod
    def from_outcome(cls, outcome: OdometerReadingOutcome) -> OdometerReadingResponse:
        return cls(
            id=outcome.reading.id,
            valor=outcome.reading.value_read,
            confianca=_CONFIANCA[outcome.reading.confidence],
            plausivel=outcome.plausible,
            ultimo_hodometro=outcome.last_odometer,
            delta=outcome.delta,
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
