import uuid
from typing import Protocol

from src.core.pagination.params import Page, PageParams
from src.modules.access.application.dtos.filters import (
    MembershipFilters,
    OrganizationFilters,
    PartnerAgreementFilters,
)
from src.modules.access.domain.entities import (
    Membership,
    MembershipWithOrganization,
    NewMembership,
    NewOrganization,
    NewPartnerAgreement,
    Organization,
    PartnerAgreement,
    UpdateMembership,
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


class MembershipRepositoryProtocol(Protocol):
    """Contrato do repositório de vínculos consumido pelos use cases de `access`."""

    async def get_by_id_or_none(self, id_: uuid.UUID) -> Membership | None: ...

    async def create(self, create_command: NewMembership) -> Membership: ...

    async def update(
        self,
        id_: uuid.UUID,
        update_command: UpdateMembership,
    ) -> Membership: ...

    async def paginate(
        self,
        page_params: PageParams,
        filters: MembershipFilters | None = None,
    ) -> Page[Membership]: ...

    async def get_active_for_user_and_organization(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Membership | None: ...

    async def is_platform_admin(self, user_id: uuid.UUID) -> bool: ...

    async def list_active_for_user(
        self,
        user_id: uuid.UUID,
    ) -> list[MembershipWithOrganization]: ...
