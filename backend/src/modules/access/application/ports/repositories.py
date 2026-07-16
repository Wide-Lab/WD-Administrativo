import uuid
from typing import Protocol

from src.core.modules import ModuleKey
from src.core.pagination.params import Page, PageParams
from src.modules.access.application.dtos.filters import (
    MembershipFilters,
    OrganizationFilters,
    PartnerAgreementFilters,
)
from src.modules.access.domain.entities import (
    Membership,
    MembershipWithOrganization,
    ModuleEntitlement,
    NewMembership,
    NewModuleEntitlement,
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


class ModuleEntitlementRepositoryProtocol(Protocol):
    """Contrato do repositório de entitlements consumido pelos use cases de `access`.

    Sem `update`: ligar é criar, desligar é apagar — não existe campo pra editar."""

    async def get_by_organization_and_module(
        self,
        organization_id: uuid.UUID,
        module_key: ModuleKey,
    ) -> ModuleEntitlement | None: ...

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
    ) -> list[ModuleEntitlement]: ...

    async def create(self, create_command: NewModuleEntitlement) -> ModuleEntitlement: ...

    async def delete(self, organization_id: uuid.UUID, module_key: ModuleKey) -> bool: ...


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
