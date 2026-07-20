"""As rotas da frota.

**Nenhuma delas declara o prefixo nem o `require_module`**: `mount_module` pendura tudo sob
`/api/organizacoes/{orgId}/frota/*` já atrás do guard de entitlement. Sair do contrato exigiria
não usar o helper — é estrutura, não disciplina (spec 05).

O que cada rota declara é a **capability**, com o `require_permission` do `core`. É o mesmo guard
que o kernel usa: nenhuma linha no `access`, nenhuma mudança no `core`."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from src.core.security import CurrentUserDep
from src.modules.frota.adapters.http.dependencies import UsageScopeDep
from src.modules.frota.adapters.http.schemas import (
    CloseUsageRequest,
    CreateDriverRequest,
    CreateUsageRequest,
    CreateVehicleRequest,
    DriverResponse,
    MileageReportResponse,
    PageResponse,
    UpdateDriverRequest,
    UpdateUsageRequest,
    UpdateVehicleRequest,
    UsageResponse,
    VehicleResponse,
)
from src.modules.frota.adapters.http.types import (
    AnyUsageWriterDep,
    DriverReaderDep,
    DriverWriterDep,
    PageParamsDep,
    UnitOfWorkDep,
    UsageReaderDep,
    UsageWriterDep,
    VehicleReaderDep,
    VehicleWriterDep,
)
from src.modules.frota.application.dtos.commands import (
    CloseUsageCommand,
    CreateDriverCommand,
    CreateUsageCommand,
    CreateVehicleCommand,
    UpdateDriverCommand,
    UpdateUsageCommand,
    UpdateVehicleCommand,
)
from src.modules.frota.application.dtos.filters import (
    DriverFilters,
    VehicleFilters,
    VehicleUsageFilters,
)
from src.modules.frota.application.use_cases.close_usage import CloseUsageUseCase
from src.modules.frota.application.use_cases.create_driver import CreateDriverUseCase
from src.modules.frota.application.use_cases.create_usage import CreateUsageUseCase
from src.modules.frota.application.use_cases.create_vehicle import CreateVehicleUseCase
from src.modules.frota.application.use_cases.delete_usage import DeleteUsageUseCase
from src.modules.frota.application.use_cases.get_driver import GetDriverUseCase
from src.modules.frota.application.use_cases.get_vehicle import GetVehicleUseCase
from src.modules.frota.application.use_cases.list_drivers import ListDriversUseCase
from src.modules.frota.application.use_cases.list_usages import ListUsagesUseCase
from src.modules.frota.application.use_cases.list_vehicles import ListVehiclesUseCase
from src.modules.frota.application.use_cases.mileage_report import MileageReportUseCase
from src.modules.frota.application.use_cases.update_driver import UpdateDriverUseCase
from src.modules.frota.application.use_cases.update_usage import UpdateUsageUseCase
from src.modules.frota.application.use_cases.update_vehicle import UpdateVehicleUseCase
from src.modules.frota.domain.entities import DriverStatus, VehicleStatus
from src.modules.frota.domain.rules import MileageGroupBy

router = APIRouter(tags=["frota"])


# --------------------------------------------------------------------------------------------
# Veículos
# --------------------------------------------------------------------------------------------


@router.get("/veiculos")
async def list_vehicles(
    _: VehicleReaderDep,
    uow: UnitOfWorkDep,
    page_params: PageParamsDep,
    status_: Annotated[VehicleStatus | None, Query(alias="status")] = None,
) -> PageResponse[VehicleResponse]:
    """Os veículos da Empresa do path.

    Veículo `inactive` continua aparecendo: some da escolha na tela, não do sistema."""

    use_case = ListVehiclesUseCase(uow=uow)
    page = await use_case.execute(
        page_params=page_params,
        filters=VehicleFilters(status=status_),
    )

    return PageResponse.of(page, [VehicleResponse.from_entity(item) for item in page.items])


@router.post("/veiculos", status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: CreateVehicleRequest,
    _: VehicleWriterDep,
    uow: UnitOfWorkDep,
) -> VehicleResponse:
    """Cadastra um veículo. Placa já existente **nesta** Empresa é 409; a mesma placa em outra
    Empresa é aceita — frota terceirizada e carro vendido de uma pra outra são reais."""

    use_case = CreateVehicleUseCase(uow=uow)
    vehicle = await use_case.execute(
        command=CreateVehicleCommand(
            plate=body.plate,
            brand=body.brand,
            model=body.model,
            model_year=body.model_year,
            initial_odometer=body.initial_odometer,
            status=body.status,
        )
    )

    return VehicleResponse.from_entity(vehicle)


@router.get("/veiculos/{id}")
async def get_vehicle(
    _: VehicleReaderDep,
    uow: UnitOfWorkDep,
    vehicle_id: Annotated[uuid.UUID, Path(alias="id")],
) -> VehicleResponse:
    """Um veículo da Empresa do path. Veículo de outra Empresa é 404, não 403."""

    use_case = GetVehicleUseCase(uow=uow)
    return VehicleResponse.from_entity(await use_case.execute(vehicle_id))


@router.patch("/veiculos/{id}")
async def update_vehicle(
    body: UpdateVehicleRequest,
    _: VehicleWriterDep,
    uow: UnitOfWorkDep,
    vehicle_id: Annotated[uuid.UUID, Path(alias="id")],
) -> VehicleResponse:
    """Edita um veículo. **Não há `DELETE`** — desativar é `status=inactive`, e o carro
    desativado continua nos relatórios do período em que rodou."""

    use_case = UpdateVehicleUseCase(uow=uow)
    vehicle = await use_case.execute(
        vehicle_id=vehicle_id,
        command=UpdateVehicleCommand(
            plate=body.plate,
            brand=body.brand,
            model=body.model,
            model_year=body.model_year,
            initial_odometer=body.initial_odometer,
            status=body.status,
        ),
    )

    return VehicleResponse.from_entity(vehicle)


# --------------------------------------------------------------------------------------------
# Condutores
# --------------------------------------------------------------------------------------------


@router.get("/condutores")
async def list_drivers(
    _: DriverReaderDep,
    uow: UnitOfWorkDep,
    page_params: PageParamsDep,
    status_: Annotated[DriverStatus | None, Query(alias="status")] = None,
) -> PageResponse[DriverResponse]:
    """Os condutores da Empresa do path."""

    use_case = ListDriversUseCase(uow=uow)
    page = await use_case.execute(
        page_params=page_params,
        filters=DriverFilters(status=status_),
    )

    return PageResponse.of(page, [DriverResponse.from_entity(item) for item in page.items])


@router.post("/condutores", status_code=status.HTTP_201_CREATED)
async def create_driver(
    body: CreateDriverRequest,
    _: DriverWriterDep,
    uow: UnitOfWorkDep,
) -> DriverResponse:
    """Cadastra um condutor.

    Condutor é entidade própria, **não** um `membership`: o motorista terceirizado dirige e nunca
    vai logar. Quem também é usuário ganha o `user_id` e passa a poder lançar a própria viagem."""

    use_case = CreateDriverUseCase(uow=uow)
    driver = await use_case.execute(
        command=CreateDriverCommand(
            name=body.name,
            user_id=body.user_id,
            license_number=body.license_number,
            license_category=body.license_category,
            license_expires_at=body.license_expires_at,
            status=body.status,
        )
    )

    return DriverResponse.from_entity(driver)


@router.get("/condutores/{id}")
async def get_driver(
    _: DriverReaderDep,
    uow: UnitOfWorkDep,
    driver_id: Annotated[uuid.UUID, Path(alias="id")],
) -> DriverResponse:
    """Um condutor da Empresa do path."""

    use_case = GetDriverUseCase(uow=uow)
    return DriverResponse.from_entity(await use_case.execute(driver_id))


@router.patch("/condutores/{id}")
async def update_driver(
    body: UpdateDriverRequest,
    _: DriverWriterDep,
    uow: UnitOfWorkDep,
    driver_id: Annotated[uuid.UUID, Path(alias="id")],
) -> DriverResponse:
    """Edita um condutor. Como no veículo, **não há `DELETE`**: desativar é `status=inactive`."""

    use_case = UpdateDriverUseCase(uow=uow)
    driver = await use_case.execute(
        driver_id=driver_id,
        command=UpdateDriverCommand(
            name=body.name,
            user_id=body.user_id,
            license_number=body.license_number,
            license_category=body.license_category,
            license_expires_at=body.license_expires_at,
            status=body.status,
        ),
    )

    return DriverResponse.from_entity(driver)


# --------------------------------------------------------------------------------------------
# Usos
# --------------------------------------------------------------------------------------------


@router.get("/usos")
async def list_usages(
    user: CurrentUserDep,
    scope: UsageScopeDep,
    uow: UnitOfWorkDep,
    page_params: PageParamsDep,
    vehicle_id: Annotated[uuid.UUID | None, Query(alias="veiculo")] = None,
    driver_id: Annotated[uuid.UUID | None, Query(alias="condutor")] = None,
    started_from: Annotated[datetime | None, Query(alias="de")] = None,
    started_until: Annotated[datetime | None, Query(alias="ate")] = None,
    only_open: Annotated[bool, Query(alias="abertos")] = False,
) -> PageResponse[UsageResponse]:
    """Os registros de uso — **o escopo é dado, não porta**.

    Esta é a única rota do módulo sem `require_permission`: ela exige só o entitlement, e o que
    devolve depende da capability. Quem tem `frota.usages.read` vê a Empresa inteira; quem não
    tem vê só os do próprio condutor (lista vazia, se não houver condutor vinculado).

    Uma rota só, e não duas: duplicá-la duplicaria paginação, filtros e ordenação pra mudar uma
    cláusula `WHERE`."""

    use_case = ListUsagesUseCase(uow=uow)
    page = await use_case.execute(
        page_params=page_params,
        scope=scope,
        user_id=user.id,
        filters=VehicleUsageFilters(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            started_from=started_from,
            started_until=started_until,
            only_open=only_open,
        ),
    )

    return PageResponse.of(page, [UsageResponse.from_entity(item) for item in page.items])


@router.post("/usos", status_code=status.HTTP_201_CREATED)
async def create_usage(
    body: CreateUsageRequest,
    user: CurrentUserDep,
    _: AnyUsageWriterDep,
    scope: UsageScopeDep,
    uow: UnitOfWorkDep,
) -> UsageResponse:
    """Lança uma viagem — inclusive retroativa, que é o caso normal.

    `started_at` no futuro é 422; veículo ou condutor inativo, 422; sobreposição de período no
    mesmo veículo, 409. Quem só tem `write_own` lança em nome de si mesmo (omitir `driver_id`
    basta) e recebe 403 ao apontar outro condutor."""

    use_case = CreateUsageUseCase(uow=uow)
    usage = await use_case.execute(
        command=CreateUsageCommand(
            vehicle_id=body.vehicle_id,
            driver_id=body.driver_id,
            started_at=body.started_at,
            ended_at=body.ended_at,
            start_odometer=body.start_odometer,
            end_odometer=body.end_odometer,
            purpose=body.purpose,
            notes=body.notes,
        ),
        scope=scope,
        user_id=user.id,
    )

    return UsageResponse.from_entity(usage)


@router.patch("/usos/{id}")
async def update_usage(
    body: UpdateUsageRequest,
    user: CurrentUserDep,
    _: AnyUsageWriterDep,
    scope: UsageScopeDep,
    uow: UnitOfWorkDep,
    usage_id: Annotated[uuid.UUID, Path(alias="id")],
) -> UsageResponse:
    """Corrige uma viagem, **inclusive uma já encerrada** — é aqui que painel trocado e
    hodômetro digitado errado se resolvem. Encerrar é a rota própria abaixo."""

    use_case = UpdateUsageUseCase(uow=uow)
    usage = await use_case.execute(
        usage_id=usage_id,
        command=UpdateUsageCommand(
            vehicle_id=body.vehicle_id,
            driver_id=body.driver_id,
            started_at=body.started_at,
            ended_at=body.ended_at,
            start_odometer=body.start_odometer,
            end_odometer=body.end_odometer,
            purpose=body.purpose,
            notes=body.notes,
        ),
        scope=scope,
        user_id=user.id,
    )

    return UsageResponse.from_entity(usage)


@router.post("/usos/{id}/encerrar")
async def close_usage(
    body: CloseUsageRequest,
    user: CurrentUserDep,
    _: AnyUsageWriterDep,
    scope: UsageScopeDep,
    uow: UnitOfWorkDep,
    usage_id: Annotated[uuid.UUID, Path(alias="id")],
) -> UsageResponse:
    """Encerra a viagem: `ended_at` + `end_odometer` juntos.

    Rota própria, e não um `PATCH`: encerrar uma viagem já encerrada é **409**, enquanto
    corrigir uma encerrada é legítimo. É o gesto mais frequente do módulo — a única coisa que o
    Colaborador faz."""

    use_case = CloseUsageUseCase(uow=uow)
    usage = await use_case.execute(
        usage_id=usage_id,
        command=CloseUsageCommand(ended_at=body.ended_at, end_odometer=body.end_odometer),
        scope=scope,
        user_id=user.id,
    )

    return UsageResponse.from_entity(usage)


@router.delete("/usos/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_usage(
    _: UsageWriterDep,
    uow: UnitOfWorkDep,
    usage_id: Annotated[uuid.UUID, Path(alias="id")],
) -> None:
    """Apaga um lançamento.

    Exige `frota.usages.write` — o `write_own` **não** alcança esta rota, e é a única do módulo
    em que as duas capabilities de escrita não se equivalem."""

    use_case = DeleteUsageUseCase(uow=uow)
    await use_case.execute(usage_id)


# --------------------------------------------------------------------------------------------
# Relatórios
# --------------------------------------------------------------------------------------------


@router.get("/relatorios/quilometragem")
async def mileage_report(
    _: UsageReaderDep,
    uow: UnitOfWorkDep,
    started_from: Annotated[datetime, Query(alias="de")],
    started_until: Annotated[datetime, Query(alias="ate")],
    group_by: Annotated[MileageGroupBy, Query(alias="agrupar_por")] = MileageGroupBy.VEHICLE,
) -> MileageReportResponse:
    """Quantos quilômetros cada veículo (ou condutor) andou no período.

    Soma `end_odometer - start_odometer` dos usos **encerrados**; os abertos entram como contagem
    à parte e nunca como zero km."""

    use_case = MileageReportUseCase(uow=uow)
    return MileageReportResponse.from_result(
        await use_case.execute(
            started_from=started_from,
            started_until=started_until,
            group_by=group_by,
        )
    )
