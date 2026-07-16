import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from src.core.pagination.params import Page
from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import (
    AgreementStatus,
    Organization,
    OrganizationStatus,
    PartnerAgreement,
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
