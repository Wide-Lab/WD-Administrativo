import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.core.tenancy import OrganizationType
from src.core.types import UNSET, BaseCreateCommand, BaseUpdateCommand, UnsetType

__all__ = [
    "AgreementStatus",
    "NewOrganization",
    "NewPartnerAgreement",
    "Organization",
    "OrganizationStatus",
    "OrganizationType",
    "PartnerAgreement",
    "UpdateOrganization",
    "UpdatePartnerAgreement",
]


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AgreementStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


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
