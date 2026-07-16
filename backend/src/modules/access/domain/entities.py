import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.core.modules import ModuleKey
from src.core.tenancy import OrganizationType
from src.core.types import UNSET, BaseCreateCommand, BaseUpdateCommand, UnsetType

__all__ = [
    "AgreementStatus",
    "Invitation",
    "InvitationStatus",
    "InvitationWithOrganization",
    "Membership",
    "MembershipStatus",
    "MembershipWithOrganization",
    "ModuleEntitlement",
    "NewInvitation",
    "NewMembership",
    "NewModuleEntitlement",
    "NewOrganization",
    "NewPartnerAgreement",
    "Organization",
    "OrganizationStatus",
    "OrganizationType",
    "PartnerAgreement",
    "Persona",
    "Role",
    "UpdateInvitation",
    "UpdateMembership",
    "UpdateOrganization",
    "UpdatePartnerAgreement",
]


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AgreementStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Role(StrEnum):
    """O papel de uma pessoa **dentro de** uma organização.

    Fixo por tipo de organização nesta fase — papéis definidos pelo cliente ganham spec
    própria se um dia forem pedidos. Qual papel vale em qual tipo é `ROLES_BY_ORGANIZATION_TYPE`
    (`domain/permissions.py`), e o banco recusa a combinação errada."""

    PLATFORM_ADMIN = "platform_admin"

    COMPANY_ADMIN = "company_admin"
    HR = "hr"
    FINANCE = "finance"
    MANAGER = "manager"
    COLLABORATOR = "collaborator"

    PARTNER_ADMIN = "partner_admin"
    PARTNER_OPERATOR = "partner_operator"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class Persona(StrEnum):
    """A superfície de frontend que o vínculo abre. Derivada do tipo da organização ativa +
    papel; não é coluna, é função dos dois (`persona_for`)."""

    PLATFORM = "platform"
    """A Widelab como operadora."""

    COMPANY_ADMIN = "company_admin"
    """Admin da Empresa — `company_admin`, `hr`, `finance` e `manager` compartilham a mesma
    superfície; o que muda entre eles são as permissões, não a casca."""

    COLLABORATOR = "collaborator"

    PARTNER = "partner"


@dataclass(frozen=True, slots=True)
class Organization:
    """Uma organização: a plataforma, uma Empresa ou um Parceiro.

    O `type` é definido na criação e **imutável** — uma pessoa jurídica que precise ser
    Empresa *e* Parceiro não é caso do produto agora; se um dia for, o caminho é migrar `type`
    pra *papéis de organização*, migração deliberada e não corrupção silenciosa."""

    id: uuid.UUID
    type: OrganizationType
    name: str
    document: str | None
    status: OrganizationStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PartnerAgreement:
    """O convênio Empresa↔Parceiro: um Parceiro atende N Empresas, e é aqui que os módulos de
    negócio (Refeições) penduram os termos **por Empresa** — catálogo, preços, subsídio.

    Esses termos comerciais não moram aqui: são dos módulos de negócio, pendurados no
    convênio."""

    id: uuid.UUID
    company_id: uuid.UUID
    partner_id: uuid.UUID
    status: AgreementStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class NewOrganization(BaseCreateCommand):
    type: OrganizationType
    name: str
    document: str | None = None
    status: OrganizationStatus = OrganizationStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateOrganization(BaseUpdateCommand):
    """Note a ausência de `type`: ele é imutável, e a aplicação não tem como atualizá-lo —
    não é regra que vive num `if`, é um campo que não existe. O banco fecha o resto, barrando
    a troca de `type` de uma organização referenciada por um convênio."""

    name: str | UnsetType = UNSET
    document: str | None | UnsetType = UNSET
    status: OrganizationStatus | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class NewPartnerAgreement(BaseCreateCommand):
    company_id: uuid.UUID
    partner_id: uuid.UUID
    status: AgreementStatus = AgreementStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdatePartnerAgreement(BaseUpdateCommand):
    status: AgreementStatus | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class Membership:
    """O vínculo usuário↔organização↔papel — a resposta a "quem é você **nesta**
    organização".

    Identidade (spec 02) é global; autorização é sempre dentro de uma organização. A mesma
    pessoa pode ser `collaborator` numa Empresa e `partner_admin` num Parceiro, e é por isso
    que papel não mora em `users` nem no token de sessão."""

    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: Role
    status: MembershipStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class MembershipWithOrganization:
    """Um vínculo já com a organização do outro lado. É o que `GET /api/me/contexto` precisa
    — listar vínculos sem o nome e o tipo da organização obrigaria o frontend a N chamadas
    pra montar o seletor de organização."""

    membership: Membership
    organization: Organization


@dataclass(frozen=True, slots=True)
class NewMembership(BaseCreateCommand):
    """Note o `organization_type`: ele é redundante com `organizations.type`, e existe pra ser
    o segundo lado da FK composta que ancora o `CHECK` de papel×tipo no banco. Quem o preenche
    é o repositório, lendo a organização — não é decisão de quem chama."""

    user_id: uuid.UUID
    organization_id: uuid.UUID
    organization_type: OrganizationType
    role: Role
    status: MembershipStatus = MembershipStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateMembership(BaseUpdateCommand):
    """Sem `organization_id` nem `user_id`: mover um vínculo de organização ou de pessoa não é
    editar, é outro vínculo. O que muda é papel e status."""

    role: Role | UnsetType = UNSET
    status: MembershipStatus | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class ModuleEntitlement:
    """ "Esta Empresa contratou este módulo" — a linha que faz a plataforma vender sem deploy.

    **Não tem coluna de habilitado/desabilitado, e isso é a decisão, não uma economia.** A
    presença da linha é o "sim" e a ausência é o "não", então o padrão de um tenant recém-criado
    é *tudo negado* sem ninguém precisar escrever nada. Um booleano teria dois jeitos de dizer
    "não" (linha ausente e linha `false`), e alguém acabaria lendo um deles errado. Desligar é
    apagar; se um dia o histórico importar, o caminho é expirar — fora de escopo agora.

    Não há `UpdateModuleEntitlement`: ligar é criar, desligar é apagar. Não existe campo pra
    editar."""

    id: uuid.UUID
    organization_id: uuid.UUID
    module_key: ModuleKey
    granted_at: datetime
    granted_by: uuid.UUID
    """Quem (`platform_admin`) liberou. Entitlement é ato comercial e tem responsável."""


@dataclass(frozen=True, slots=True)
class NewModuleEntitlement(BaseCreateCommand):
    """Note a ausência de `organization_type`: diferente do vínculo (`NewMembership`), aqui o
    tipo não é escolha nem leitura — é uma constante gerada pelo banco, porque só Empresa
    contrata módulo. Ver o model."""

    organization_id: uuid.UUID
    module_key: ModuleKey
    granted_by: uuid.UUID


class InvitationStatus(StrEnum):
    """O ciclo de um convite.

    `EXPIRED` **nunca é gravado** pela aplicação, e isso é decisão: quem sabe se um convite
    venceu é `expires_at`, comparado com o agora. Gravar o status exigiria um cron pra manter
    a coluna honesta, e até ele rodar um convite vencido responderia `pending` — duas fontes
    da verdade divergindo justamente no instante que importa. O valor existe no enum porque a
    spec o declara e porque um sweeper futuro (ou um relatório) tem onde escrever; hoje,
    `effective_status` o deriva. Ver `Como ficou` da spec 06."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class Invitation:
    """Um convite pra entrar numa organização com um papel já definido.

    É o caminho de entrada do Colaborador e do staff da Empresa, que **não** se
    auto-cadastram: alguém com `invitations.write` decide o papel antes de a pessoa existir. O
    Parceiro entra pelo outro caminho (auto-cadastro), e é por isso que os dois fluxos da spec
    06 são deliberadamente diferentes.

    O convite carrega o papel, e não o vínculo: vínculo só nasce no aceite. Enquanto pendente,
    não há `membership` nenhum — um convite não dá acesso a nada."""

    id: uuid.UUID
    email: str
    organization_id: uuid.UUID
    role: Role
    token: str
    status: InvitationStatus
    expires_at: datetime
    invited_by: uuid.UUID
    created_at: datetime

    def effective_status(self, now: datetime) -> InvitationStatus:
        """O status de verdade, com a expiração já resolvida.

        Um convite `pending` cujo `expires_at` passou é `EXPIRED` — sem depender de ninguém ter
        rodado um sweeper. É esta função, e não a coluna, que o aceite consulta."""

        if self.status is InvitationStatus.PENDING and now >= self.expires_at:
            return InvitationStatus.EXPIRED
        return self.status

    def is_open(self, now: datetime) -> bool:
        """Se o convite ainda pode ser aceito."""

        return self.effective_status(now) is InvitationStatus.PENDING


@dataclass(frozen=True, slots=True)
class InvitationWithOrganization:
    """Um convite já com a organização do outro lado — o que a tela pública de aceite precisa
    (`GET /api/convites/{token}` mostra o nome da Empresa que convidou)."""

    invitation: Invitation
    organization: Organization


@dataclass(frozen=True, slots=True)
class NewInvitation(BaseCreateCommand):
    """Como em `NewMembership`, o `organization_type` é o segundo lado da FK composta que
    ancora o `CHECK` de papel×tipo — quem o preenche é o use case lendo a organização, não
    quem chama a rota. Convidar um `hr` pra um Parceiro é impossível **no banco**, e não só
    aqui."""

    email: str
    organization_id: uuid.UUID
    organization_type: OrganizationType
    role: Role
    token: str
    expires_at: datetime
    invited_by: uuid.UUID
    status: InvitationStatus = InvitationStatus.PENDING


@dataclass(frozen=True, slots=True)
class UpdateInvitation(BaseUpdateCommand):
    """Só o status muda. Mudar o papel ou o e-mail de um convite pendente seria outro convite
    — e o token já saiu por e-mail dizendo o que dizia."""

    status: InvitationStatus | UnsetType = UNSET
