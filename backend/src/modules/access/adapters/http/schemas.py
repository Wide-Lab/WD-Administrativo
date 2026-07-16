import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field

from src.core.modules import ModuleDescriptor, ModuleNav
from src.core.pagination.params import Page
from src.core.tenancy import OrganizationType
from src.modules.access.application.use_cases.get_my_membership import MyMembership
from src.modules.access.application.use_cases.list_modules import OrganizationModules
from src.modules.access.domain.entities import (
    AgreementStatus,
    Invitation,
    InvitationStatus,
    InvitationWithOrganization,
    Membership,
    MembershipStatus,
    MembershipWithOrganization,
    ModuleEntitlement,
    Organization,
    OrganizationStatus,
    PartnerAgreement,
    Persona,
    Role,
)


class CreatableOrganizationType(StrEnum):
    """Os tipos que a API cria. `platform` não está aqui: é a Widelab como operadora,
    exatamente uma linha, semeada na migration — e o índice único parcial do banco recusaria
    uma segunda de qualquer forma."""

    COMPANY = "company"
    PARTNER = "partner"


class CreateOrganizationRequest(BaseModel):
    type: CreatableOrganizationType
    name: str = Field(min_length=1)
    document: str | None = None


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    type: OrganizationType
    name: str
    document: str | None
    status: OrganizationStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Organization) -> OrganizationResponse:
        return cls(
            id=entity.id,
            type=entity.type,
            name=entity.name,
            document=entity.document,
            status=entity.status,
            created_at=entity.created_at,
        )


class CreateAgreementRequest(BaseModel):
    """A Empresa não vem no corpo: é a organização do path. Aceitá-la aqui abriria conveniar
    em nome de outra."""

    partner_id: uuid.UUID


class UpdateAgreementRequest(BaseModel):
    status: AgreementStatus


class AgreementResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    partner_id: uuid.UUID
    status: AgreementStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: PartnerAgreement) -> AgreementResponse:
        return cls(
            id=entity.id,
            company_id=entity.company_id,
            partner_id=entity.partner_id,
            status=entity.status,
            created_at=entity.created_at,
        )


class MeSummary(BaseModel):
    """A identidade dentro do contexto. Repete o `GET /api/me` de propósito: o contexto é o
    bootstrap do frontend, e obrigá-lo a duas chamadas pra pintar o cabeçalho seria pior."""

    id: uuid.UUID
    email: str
    name: str


class ContextOrganization(BaseModel):
    id: uuid.UUID
    type: OrganizationType
    name: str


class ContextMembership(BaseModel):
    organization: ContextOrganization
    role: Role

    @classmethod
    def from_entity(cls, entity: MembershipWithOrganization) -> ContextMembership:
        return cls(
            organization=ContextOrganization(
                id=entity.organization.id,
                type=entity.organization.type,
                name=entity.organization.name,
            ),
            role=entity.membership.role,
        )


class MyContextResponse(BaseModel):
    """`GET /api/me/contexto` — o bootstrap de roteamento e do seletor de organização."""

    user: MeSummary
    memberships: list[ContextMembership]


class MyMembershipResponse(BaseModel):
    """`GET /api/organizacoes/{orgId}/me` — minha situação **nesta** organização.

    `modules` entrou aqui na spec 05, como a 04 previu. Um `[]` agora significa o que diz — a
    Empresa não contratou nada —, e não mais "entitlement não existe"."""

    role: Role
    persona: Persona
    permissions: list[str]

    modules: list[str]
    """As chaves dos módulos habilitados **da organização**. A casca cruza com `permissions`
    pra montar a navegação; o backend nega igual sem ela."""

    @classmethod
    def from_result(cls, result: MyMembership) -> MyMembershipResponse:
        return cls(
            role=result.role,
            persona=result.persona,
            permissions=sorted(result.permissions),
            modules=sorted(result.modules),
        )


class ModuleNavResponse(BaseModel):
    """Os metadados de navegação que o módulo declara no descritor."""

    label: str
    path: str
    icon: str | None

    @classmethod
    def from_descriptor(cls, nav: ModuleNav) -> ModuleNavResponse:
        return cls(label=nav.label, path=nav.path, icon=nav.icon)


class CatalogModuleResponse(BaseModel):
    """Um módulo do catálogo: o que a **plataforma** sabe oferecer, ligado ou não.

    Sem `permissions`: o catálogo diz o que dá pra vender, e as capabilities de dentro do
    módulo são pergunta do `/me` de cada pessoa, não desta lista."""

    key: str
    name: str
    personas: list[str]
    nav: ModuleNavResponse

    @classmethod
    def from_descriptor(cls, descriptor: ModuleDescriptor) -> CatalogModuleResponse:
        return cls(
            key=descriptor.key,
            name=descriptor.name,
            personas=list(descriptor.personas),
            nav=ModuleNavResponse.from_descriptor(descriptor.nav),
        )


class EnabledModuleResponse(BaseModel):
    """Um módulo habilitado: um fato sobre **este tenant** — quem ligou e quando."""

    key: str
    granted_at: datetime
    granted_by: uuid.UUID

    @classmethod
    def from_entity(cls, entity: ModuleEntitlement) -> EnabledModuleResponse:
        return cls(
            key=entity.module_key,
            granted_at=entity.granted_at,
            granted_by=entity.granted_by,
        )


class OrganizationModulesResponse(BaseModel):
    """`GET /api/organizacoes/{orgId}/modulos` — o que esta Empresa contratou e o que existe
    pra contratar.

    As duas listas não se repetem: cruzar por `key` é do frontend. `catalog` é igual pra toda
    organização; `enabled` é o que muda de tenant pra tenant."""

    enabled: list[EnabledModuleResponse]
    catalog: list[CatalogModuleResponse]

    @classmethod
    def from_result(cls, result: OrganizationModules) -> OrganizationModulesResponse:
        return cls(
            enabled=[EnabledModuleResponse.from_entity(item) for item in result.enabled],
            catalog=[CatalogModuleResponse.from_descriptor(item) for item in result.catalog],
        )


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: Role
    status: MembershipStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Membership) -> MemberResponse:
        return cls(
            id=entity.id,
            user_id=entity.user_id,
            organization_id=entity.organization_id,
            role=entity.role,
            status=entity.status,
            created_at=entity.created_at,
        )


class UpdateMemberRequest(BaseModel):
    """Papel e status são opcionais, mas ao menos um é exigido — o use case recusa o corpo
    vazio com 422. Criar membro não passa por aqui: é convite (spec 06)."""

    role: Role | None = None
    status: MembershipStatus | None = None


class CreateInvitationRequest(BaseModel):
    """A organização não vem no corpo: é a do path. Aceitá-la aqui abriria convidar em nome de
    outra — o critério 4 da spec 06."""

    email: EmailStr
    role: Role


class InvitationResponse(BaseModel):
    """O convite como quem convidou o vê.

    **Sem o `token`**: ele é credencial e sai por e-mail, para o convidado. Devolvê-lo aqui
    deixaria qualquer `hr` aceitar o convite que emitiu no lugar da pessoa, e o e-mail deixaria
    de ser a prova de que quem aceitou controla a caixa."""

    id: uuid.UUID
    email: EmailStr
    organization_id: uuid.UUID
    role: Role
    status: InvitationStatus
    expires_at: datetime
    invited_by: uuid.UUID
    created_at: datetime

    @classmethod
    def from_entity(cls, entity: Invitation) -> InvitationResponse:
        return cls(
            id=entity.id,
            email=entity.email,
            organization_id=entity.organization_id,
            role=entity.role,
            status=entity.status,
            expires_at=entity.expires_at,
            invited_by=entity.invited_by,
            created_at=entity.created_at,
        )


class PublicInvitationResponse(BaseModel):
    """`GET /api/convites/{token}` — o mínimo que a tela pública de aceite precisa pintar.

    Público, então cada campo é uma decisão: o nome da organização e o papel explicam à pessoa
    o que ela está aceitando, e o e-mail deixa a tela dizer para quem o convite é sem pedir que
    ela o digite. Nada de ids internos — quem ainda não aceitou não é membro de nada."""

    organization_name: str
    email: EmailStr
    role: Role
    expires_at: datetime

    @classmethod
    def from_entity(cls, entity: InvitationWithOrganization) -> PublicInvitationResponse:
        return cls(
            organization_name=entity.organization.name,
            email=entity.invitation.email,
            role=entity.invitation.role,
            expires_at=entity.invitation.expires_at,
        )


class AcceptInvitationRequest(BaseModel):
    """`name` é opcional porque quem já tem conta já tem nome. A senha segue a mesma política
    do `PUT /api/me/password` (spec 02) — 8 caracteres."""

    password: str = Field(min_length=8)
    name: str | None = Field(default=None, min_length=1)


class RegisterPartnerAdminRequest(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterPartnerRequest(BaseModel):
    """`POST /api/parceiros/cadastro`.

    `company_name` é o nome do **Parceiro**, não de uma Empresa — o nome do campo é o que a
    spec 06 fixou no payload, e mudá-lo aqui seria mudar o contrato. Ver `Como ficou`."""

    company_name: str = Field(min_length=1)
    admin: RegisterPartnerAdminRequest
    document: str | None = None


class PageResponse[ItemT](BaseModel):
    """A `Page` do `core` traduzida pra resposta da API."""

    items: list[ItemT]
    total: int
    page: int
    page_size: int

    @classmethod
    def of[EntityT](
        cls,
        page: Page[EntityT],
        items: list[ItemT],
    ) -> PageResponse[ItemT]:
        return cls(
            items=items,
            total=page.total,
            page=page.page,
            page_size=page.page_size,
        )
