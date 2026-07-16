import uuid
from dataclasses import dataclass

from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import MembershipStatus, Role


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
