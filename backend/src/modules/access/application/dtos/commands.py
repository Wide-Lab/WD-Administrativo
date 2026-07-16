import uuid
from dataclasses import dataclass

from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import AgreementStatus, MembershipStatus, Role


@dataclass(frozen=True, slots=True)
class CreateOrganizationCommand:
    """Provisiona um tenant. `type` entra aqui e nunca mais muda."""

    type: OrganizationType
    name: str
    document: str | None = None


@dataclass(frozen=True, slots=True)
class CreateAgreementCommand:
    """Vincula um Parceiro à Empresa ativa. A Empresa é a organização do path — não vem no
    corpo, senão daria pra conveniar em nome de outra."""

    partner_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class UpdateAgreementStatusCommand:
    status: AgreementStatus


@dataclass(frozen=True, slots=True)
class UpdateMembershipCommand:
    """Muda papel e/ou status de um membro. Os dois são opcionais e ao menos um é exigido —
    `None` aqui é "não mexe", não "apaga"."""

    role: Role | None = None
    status: MembershipStatus | None = None
