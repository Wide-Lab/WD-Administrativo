import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from src.core.notifications import EmailSenderDep
from src.core.security import CurrentUserDep, UserDirectoryDep, issue_session, set_session_cookie
from src.core.tenancy import CurrentOrganizationDep, OrganizationType
from src.modules.access.adapters.http.schemas import (
    AcceptInvitationRequest,
    AgreementResponse,
    ContextMembership,
    CreateAgreementRequest,
    CreateInvitationRequest,
    CreateOrganizationRequest,
    EnabledModuleResponse,
    InvitationResponse,
    MemberResponse,
    MeSummary,
    MyContextResponse,
    MyMembershipResponse,
    OrganizationModulesResponse,
    OrganizationResponse,
    PageResponse,
    PublicInvitationResponse,
    RegisterPartnerRequest,
    UpdateAgreementRequest,
    UpdateMemberRequest,
)
from src.modules.access.adapters.http.types import (
    AgreementWriterDep,
    InvitationWriterDep,
    MemberReaderDep,
    MemberWriterDep,
    ModuleReaderDep,
    ModuleWriterDep,
    PageParamsDep,
    PlatformAdminDep,
    UnitOfWorkDep,
)
from src.modules.access.application.dtos.commands import (
    AcceptInvitationCommand,
    CreateAgreementCommand,
    CreateInvitationCommand,
    CreateOrganizationCommand,
    RegisterPartnerCommand,
    UpdateAgreementStatusCommand,
    UpdateMembershipCommand,
)
from src.modules.access.application.dtos.filters import OrganizationFilters
from src.modules.access.application.use_cases.accept_invitation import AcceptInvitationUseCase
from src.modules.access.application.use_cases.create_agreement import CreateAgreementUseCase
from src.modules.access.application.use_cases.create_invitation import CreateInvitationUseCase
from src.modules.access.application.use_cases.create_organization import (
    CreateOrganizationUseCase,
)
from src.modules.access.application.use_cases.disable_module import DisableModuleUseCase
from src.modules.access.application.use_cases.enable_module import EnableModuleUseCase
from src.modules.access.application.use_cases.get_invitation import GetInvitationUseCase
from src.modules.access.application.use_cases.get_my_context import GetMyContextUseCase
from src.modules.access.application.use_cases.get_my_membership import GetMyMembershipUseCase
from src.modules.access.application.use_cases.get_organization import GetOrganizationUseCase
from src.modules.access.application.use_cases.list_agreements import ListAgreementsUseCase
from src.modules.access.application.use_cases.list_members import ListMembersUseCase
from src.modules.access.application.use_cases.list_modules import ListModulesUseCase
from src.modules.access.application.use_cases.list_organizations import (
    ListOrganizationsUseCase,
)
from src.modules.access.application.use_cases.register_partner import RegisterPartnerUseCase
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
    Papel e permissões *dentro* de uma organização vêm do `GET /api/organizacoes/{orgId}/me`.
    401 se não logado."""

    use_case = GetMyContextUseCase(uow=uow)
    memberships = await use_case.execute(user_id=user.id)

    return MyContextResponse(
        user=MeSummary(id=user.id, email=user.email, name=user.name),
        memberships=[ContextMembership.from_entity(item) for item in memberships],
    )


@router.get("/organizacoes/{orgId}/me")
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


@router.get("/organizacoes/{orgId}/modulos")
async def list_modules(
    organization: ModuleReaderDep,
    uow: UnitOfWorkDep,
) -> OrganizationModulesResponse:
    """Os módulos habilitados da Empresa do path, mais o catálogo do que dá pra habilitar.

    Visão de plataforma: é a tela de quem vende. Quem consome módulo não pergunta aqui — o
    `GET /api/organizacoes/{orgId}/me` já devolve as chaves habilitadas."""

    use_case = ListModulesUseCase(uow=uow)
    return OrganizationModulesResponse.from_result(await use_case.execute(organization))


@router.put("/organizacoes/{orgId}/modulos/{chave}")
async def enable_module(
    user: CurrentUserDep,
    organization: ModuleWriterDep,
    uow: UnitOfWorkDep,
    module_key: Annotated[str, Path(alias="chave")],
) -> EnabledModuleResponse:
    """Habilita um módulo na Empresa do path — vender é ligar o flag, sem deploy.

    Idempotente: habilitar o que já está habilitado devolve 200 com o mesmo entitlement."""

    use_case = EnableModuleUseCase(uow=uow)
    entitlement = await use_case.execute(
        organization=organization,
        module_key=module_key,
        granted_by=user.id,
    )

    return EnabledModuleResponse.from_entity(entitlement)


@router.delete("/organizacoes/{orgId}/modulos/{chave}", status_code=status.HTTP_204_NO_CONTENT)
async def disable_module(
    organization: ModuleWriterDep,
    uow: UnitOfWorkDep,
    module_key: Annotated[str, Path(alias="chave")],
) -> None:
    """Desabilita um módulo na Empresa do path, apagando o entitlement.

    A partir daqui as rotas do módulo voltam a responder 403. Idempotente: desabilitar o que já
    está desabilitado é 204 também — o `DELETE` afirma um estado, e ele já é esse."""

    use_case = DisableModuleUseCase(uow=uow)
    await use_case.execute(organization=organization, module_key=module_key)


@router.post(
    "/organizacoes/{orgId}/convites",
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    body: CreateInvitationRequest,
    user: CurrentUserDep,
    organization: InvitationWriterDep,
    uow: UnitOfWorkDep,
    email_sender: EmailSenderDep,
) -> InvitationResponse:
    """Convida alguém pra organização do path, com o papel já definido.

    É o caminho de entrada do Colaborador e do staff da Empresa, que não se auto-cadastram.
    Um `hr` só convida pra **sua** organização: a permissão é resolvida no `orgId` do path."""

    use_case = CreateInvitationUseCase(uow=uow, email_sender=email_sender)
    invitation = await use_case.execute(
        organization=organization,
        invited_by=user,
        command=CreateInvitationCommand(email=body.email, role=body.role),
    )

    return InvitationResponse.from_entity(invitation)


@router.get("/convites/{token}")
async def get_invitation(
    uow: UnitOfWorkDep,
    token: Annotated[str, Path()],
) -> PublicInvitationResponse:
    """Os dados públicos mínimos da tela de aceite. **Sem sessão** — quem vai aceitar ainda não
    tem uma; o que autoriza é o token.

    404 se o token nunca existiu, 410 se existiu e não vale mais."""

    use_case = GetInvitationUseCase(uow=uow)
    return PublicInvitationResponse.from_entity(await use_case.execute(token))


@router.post("/convites/{token}/aceitar")
async def accept_invitation(
    body: AcceptInvitationRequest,
    response: Response,
    uow: UnitOfWorkDep,
    directory: UserDirectoryDep,
    token: Annotated[str, Path()],
) -> None:
    """Aceita o convite e já entra: cria o login se não houver, cria o vínculo e emite sessão.

    Responde 200 sem corpo, como o `POST /api/auth/login` — a identidade vem do `GET /api/me`,
    e devolver o usuário aqui seria uma segunda fonte da verdade.

    A resposta é a mesma para quem já tinha conta e para quem não tinha: o token prova controle
    da caixa de e-mail, e o corpo não pode virar um oráculo de quem já é cadastrado."""

    use_case = AcceptInvitationUseCase(uow=uow, directory=directory)
    user_id = await use_case.execute(
        command=AcceptInvitationCommand(
            token=token,
            password=body.password,
            name=body.name,
        ),
    )

    set_session_cookie(response, issue_session(user_id))


@router.post("/parceiros/cadastro", status_code=status.HTTP_201_CREATED)
async def register_partner(
    body: RegisterPartnerRequest,
    response: Response,
    uow: UnitOfWorkDep,
    directory: UserDirectoryDep,
) -> None:
    """Auto-cadastro de Parceiro: organização, primeiro `partner_admin` e vínculo, numa
    transação — mais a sessão.

    Rota **pública**, e a única que cria organização sem `platform_admin`: o Parceiro é
    organização de primeiro nível. Isso não lhe dá acesso a Empresa nenhuma — quem o liga a
    cada uma é o convênio (spec 03), que segue sendo ato da Empresa.

    E-mail já cadastrado responde 409, sem deixar organização órfã."""

    use_case = RegisterPartnerUseCase(uow=uow, directory=directory)
    user_id = await use_case.execute(
        command=RegisterPartnerCommand(
            company_name=body.company_name,
            document=body.document,
            admin_name=body.admin.name,
            admin_email=body.admin.email,
            admin_password=body.admin.password,
        ),
    )

    set_session_cookie(response, issue_session(user_id))


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
