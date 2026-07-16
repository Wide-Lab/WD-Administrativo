import uuid
from typing import Protocol

from src.core.pagination.params import Page, PageParams
from src.modules.access.application.dtos.filters import (
    OrganizationFilters,
    PartnerAgreementFilters,
)
from src.modules.access.domain.entities import (
    NewOrganization,
    NewPartnerAgreement,
    Organization,
    PartnerAgreement,
    UpdateOrganization,
    UpdatePartnerAgreement,
)


class OrganizationRepositoryProtocol(Protocol):
    """Contrato do repositório de organizações consumido pelos use cases de `access`."""

    async def get_by_id_or_none(self, id_: uuid.UUID) -> Organization | None: ...

    async def create(self, create_command: NewOrganization) -> Organization: ...

    async def update(
        self,
        id_: uuid.UUID,
        update_command: UpdateOrganization,
    ) -> Organization: ...

    async def paginate(
        self,
        page_params: PageParams,
        filters: OrganizationFilters | None = None,
    ) -> Page[Organization]: ...


class PartnerAgreementRepositoryProtocol(Protocol):
    """Contrato do repositório de convênios consumido pelos use cases de `access`."""

    async def get_by_id_or_none(self, id_: uuid.UUID) -> PartnerAgreement | None: ...

    async def create(self, create_command: NewPartnerAgreement) -> PartnerAgreement: ...

    async def update(
        self,
        id_: uuid.UUID,
        update_command: UpdatePartnerAgreement,
    ) -> PartnerAgreement: ...

    async def paginate(
        self,
        page_params: PageParams,
        filters: PartnerAgreementFilters | None = None,
    ) -> Page[PartnerAgreement]: ...
