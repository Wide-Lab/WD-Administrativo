import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from src.core.security import CurrentUserDep
from src.core.tenancy import CurrentOrganizationDep, OrganizationType
from src.modules.access.adapters.http.schemas import (
    AgreementResponse,
    ContextMembership,
    CreateAgreementRequest,
    CreateOrganizationRequest,
    MemberResponse,
    MeSummary,
    MyContextResponse,
    MyMembershipResponse,
    OrganizationResponse,
    PageResponse,
    UpdateAgreementRequest,
    UpdateMemberRequest,
)
from src.modules.access.adapters.http.types import (
    AgreementWriterDep,
    MemberReaderDep,
    MemberWriterDep,
    PageParamsDep,
    PlatformAdminDep,
    UnitOfWorkDep,
)
from src.modules.access.application.dtos.commands import (
    CreateAgreementCommand,
    CreateOrganizationCommand,
    UpdateAgreementStatusCommand,
    UpdateMembershipCommand,
)
from src.modules.access.application.dtos.filters import OrganizationFilters
from src.modules.access.application.use_cases.create_agreement import CreateAgreementUseCase
from src.modules.access.application.use_cases.create_organization import (
    CreateOrganizationUseCase,
)
from src.modules.access.application.use_cases.get_my_context import GetMyContextUseCase
from src.modules.access.application.use_cases.get_my_membership import GetMyMembershipUseCase
from src.modules.access.application.use_cases.get_organization import GetOrganizationUseCase
from src.modules.access.application.use_cases.list_agreements import ListAgreementsUseCase
from src.modules.access.application.use_cases.list_members import ListMembersUseCase
from src.modules.access.application.use_cases.list_organizations import (
    ListOrganizationsUseCase,
)
from src.modules.access.application.use_cases.update_agreement_status import (
    UpdateAgreementStatusUseCase,
)
from src.modules.access.application.use_cases.update_membership import UpdateMembershipUseCase

router = APIRouter(tags=["access"])


@router.get("/me/contexto")
async def my_context(
    user: CurrentUserDep,
    uow: UnitOfWorkDep,
) -> MyContextResponse:
    """Meus vínculos — o bootstrap de roteamento e do seletor de organização.

    Global, e não escopado por tenant: é a pergunta que **precede** a escolha do `orgId`.
    Papel e permissões *dentro* de uma organização vêm do `GET /api/organizacoes/{orgId}/eu`.
    401 se não logado."""

    use_case = GetMyContextUseCase(uow=uow)
    memberships = await use_case.execute(user_id=user.id)

    return MyContextResponse(
        user=MeSummary(id=user.id, email=user.email, name=user.name),
        memberships=[ContextMembership.from_entity(item) for item in memberships],
    )


@router.get("/organizacoes/{orgId}/eu")
async def my_membership(
    user: CurrentUserDep,
    organization: CurrentOrganizationDep,
    uow: UnitOfWorkDep,
) -> MyMembershipResponse:
    """Eu **nesta** organização: papel, persona e permissões.

    Trocar de contexto é chamar isto com outro `orgId` — a mesma sessão devolve personas e
    permissões diferentes, sem novo login, porque não há papel nem organização no token."""

    use_case = GetMyMembershipUseCase(uow=uow)
    return MyMembershipResponse.from_result(
        await use_case.execute(user_id=user.id, organization=organization)
    )


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
    organization: AgreementWriterDep,
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
    organization: AgreementWriterDep,
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


@router.get("/organizacoes/{orgId}/membros")
async def list_members(
    organization: MemberReaderDep,
    uow: UnitOfWorkDep,
    page_params: PageParamsDep,
) -> PageResponse[MemberResponse]:
    """Lista os membros da organização do path."""

    use_case = ListMembersUseCase(uow=uow)
    page = await use_case.execute(organization=organization, page_params=page_params)

    return PageResponse.of(
        page,
        [MemberResponse.from_entity(item) for item in page.items],
    )


@router.patch("/organizacoes/{orgId}/membros/{id}")
async def update_member(
    body: UpdateMemberRequest,
    organization: MemberWriterDep,
    uow: UnitOfWorkDep,
    membership_id: Annotated[uuid.UUID, Path(alias="id")],
) -> MemberResponse:
    """Muda papel ou status de um membro. Criar membro é via convite (spec 06), não POST."""

    use_case = UpdateMembershipUseCase(uow=uow)
    membership = await use_case.execute(
        organization=organization,
        membership_id=membership_id,
        command=UpdateMembershipCommand(role=body.role, status=body.status),
    )

    return MemberResponse.from_entity(membership)
