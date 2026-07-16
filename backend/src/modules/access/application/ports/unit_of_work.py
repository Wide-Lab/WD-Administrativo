from types import TracebackType
from typing import Protocol, Self

from src.modules.access.application.ports.repositories import (
    MembershipRepositoryProtocol,
    OrganizationRepositoryProtocol,
    PartnerAgreementRepositoryProtocol,
)


class AccessUnitOfWorkProtocol(Protocol):
    @property
    def organizations(self) -> OrganizationRepositoryProtocol: ...

    @property
    def agreements(self) -> PartnerAgreementRepositoryProtocol: ...

    @property
    def memberships(self) -> MembershipRepositoryProtocol: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
