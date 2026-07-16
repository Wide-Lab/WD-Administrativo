import uuid
from dataclasses import dataclass

from src.core.tenancy import OrganizationType


@dataclass(frozen=True, slots=True)
class OrganizationFilters:
    type: OrganizationType | None = None


@dataclass(frozen=True, slots=True)
class PartnerAgreementFilters:
    organization_id: uuid.UUID | None = None
    """Filtra os convênios de que a organização participa — de qualquer um dos dois lados."""
