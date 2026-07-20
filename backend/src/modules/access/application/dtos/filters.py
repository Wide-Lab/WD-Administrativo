import uuid
from dataclasses import dataclass
from datetime import datetime

from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import InvitationStatus, MembershipStatus, Role


@dataclass(frozen=True, slots=True)
class OrganizationFilters:
    type: OrganizationType | None = None


@dataclass(frozen=True, slots=True)
class PartnerAgreementFilters:
    organization_id: uuid.UUID | None = None
    """Filtra os convênios de que a organização participa — de qualquer um dos dois lados."""


@dataclass(frozen=True, slots=True)
class MembershipFilters:
    organization_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    role: Role | None = None
    status: MembershipStatus | None = None


@dataclass(frozen=True, slots=True)
class InvitationFilters:
    """Note que `status` é o **efetivo**, não a coluna — e é por isso que `now` viaja junto.

    Um convite vencido tem `status = 'pending'` no banco e `expired` na verdade (spec 06:
    `expired` nunca é gravado). Filtrar pela coluna devolveria vencidos na lista de pendentes,
    que é exatamente a pergunta que a rota existe pra responder errado.

    O `now` vem de quem chama, e não de um `now()` do Postgres, pra a listagem e o
    `Invitation.effective_status` responderem pelo **mesmo** instante: são duas leituras da
    mesma regra, e um relógio por conta faria a lista discordar do item."""

    organization_id: uuid.UUID | None = None
    status: InvitationStatus | None = None
    now: datetime | None = None
