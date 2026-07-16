import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from src.core.tenancy import CurrentOrganizationDep, OrganizationType
from src.modules.access.adapters.http.schemas import (
    AgreementResponse,
    CreateAgreementRequest,
    CreateOrganizationRequest,
    OrganizationResponse,
    PageResponse,
    UpdateAgreementRequest,
)
from src.modules.access.adapters.http.types import (
    CompanyAdminDep,
    PageParamsDep,
    PlatformAdminDep,
    UnitOfWorkDep,
)
from src.modules.access.application.dtos.commands import (
    CreateAgreementCommand,
    CreateOrganizationCommand,
    UpdateAgreementStatusCommand,
)
from src.modules.access.application.dtos.filters import OrganizationFilters
from src.modules.access.application.use_cases.create_agreement import CreateAgreementUseCase
from src.modules.access.application.use_cases.create_organization import (
    CreateOrganizationUseCase,
)
from src.modules.access.application.use_cases.get_organization import GetOrganizationUseCase
from src.modules.access.application.use_cases.list_agreements import ListAgreementsUseCase
from src.modules.access.application.use_cases.list_organizations import (
    ListOrganizationsUseCase,
)
from src.modules.access.application.use_cases.update_agreement_status import (
    UpdateAgreementStatusUseCase,
)

router = APIRouter(tags=["access"])


@router.post(
    "/organizacoes",
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    body: CreateOrganizationRequest,
    _: PlatformAdminDep,
    uow: UnitOfWorkDep,
) -> OrganizationResponse:
    """Provisiona um tenant: uma Empresa ou um Parceiro.

    `platform` não se cria por aqui — é a Widelab como operadora, semeada na migration."""

    use_case = CreateOrganizationUseCase(uow=uow)
    organization = await use_case.execute(
        command=CreateOrganizationCommand(
            type=OrganizationType(body.type.value),
            name=body.name,
            document=body.document,
        ),
    )

    return OrganizationResponse.from_entity(organization)


@router.get("/organizacoes")
async def list_organizations(
    _: PlatformAdminDep,
    uow: UnitOfWorkDep,
    page_params: PageParamsDep,
    type_: Annotated[OrganizationType | None, Query(alias="tipo")] = None,
) -> PageResponse[OrganizationResponse]:
    """Lista os tenants. Visão de plataforma — não é escopada por organização."""

    use_case = ListOrganizationsUseCase(uow=uow)
    page = await use_case.execute(
        page_params=page_params,
        filters=OrganizationFilters(type=type_),
    )

    return PageResponse.of(
        page,
        [OrganizationResponse.from_entity(item) for item in page.items],
    )


@router.get("/organizacoes/{orgId}")
async def get_organization(
    organization: CurrentOrganizationDep,
    uow: UnitOfWorkDep,
) -> OrganizationResponse:
    """Detalha a organização do path. 403 se quem pediu não a alcança."""

    use_case = GetOrganizationUseCase(uow=uow)
    return OrganizationResponse.from_entity(await use_case.execute(organization.id))


@router.post(
    "/organizacoes/{orgId}/convenios",
    status_code=status.HTTP_201_CREATED,
)
async def create_agreement(
    body: CreateAgreementRequest,
    organization: CompanyAdminDep,
    uow: UnitOfWorkDep,
) -> AgreementResponse:
    """Vincula um Parceiro à Empresa do path."""

    use_case = CreateAgreementUseCase(uow=uow)
    agreement = await use_case.execute(
        organization=organization,
        command=CreateAgreementCommand(partner_id=body.partner_id),
    )

    return AgreementResponse.from_entity(agreement)


@router.get("/organizacoes/{orgId}/convenios")
async def list_agreements(
    organization: CurrentOrganizationDep,
    uow: UnitOfWorkDep,
    page_params: PageParamsDep,
) -> PageResponse[AgreementResponse]:
    """Lista os convênios da organização do path — serve à Empresa e ao Parceiro."""

    use_case = ListAgreementsUseCase(uow=uow)
    page = await use_case.execute(organization=organization, page_params=page_params)

    return PageResponse.of(
        page,
        [AgreementResponse.from_entity(item) for item in page.items],
    )


@router.patch("/organizacoes/{orgId}/convenios/{id}")
async def update_agreement(
    body: UpdateAgreementRequest,
    organization: CompanyAdminDep,
    uow: UnitOfWorkDep,
    agreement_id: Annotated[uuid.UUID, Path(alias="id")],
) -> AgreementResponse:
    """Suspende ou reativa um convênio da Empresa do path."""

    use_case = UpdateAgreementStatusUseCase(uow=uow)
    agreement = await use_case.execute(
        organization=organization,
        agreement_id=agreement_id,
        command=UpdateAgreementStatusCommand(status=body.status),
    )

    return AgreementResponse.from_entity(agreement)
