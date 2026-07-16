from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.unit_of_work import SQLAlchemyUnitOfWork
from src.modules.access.adapters.db.repository import (
    MembershipRepository,
    ModuleEntitlementRepository,
    OrganizationRepository,
    PartnerAgreementRepository,
)


class AccessUnitOfWork(SQLAlchemyUnitOfWork):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """
        Inicializa a unidade de trabalho de organizações e tenancy.

        Args:
            session (AsyncSession):
                Sessão do banco de dados.
        """

        super().__init__(session=session)
        self._organizations: OrganizationRepository | None = None
        self._agreements: PartnerAgreementRepository | None = None
        self._memberships: MembershipRepository | None = None
        self._module_entitlements: ModuleEntitlementRepository | None = None

    @property
    def organizations(self) -> OrganizationRepository:
        """Repositório de organizações."""
        if self._organizations is None:
            raise RuntimeError("Repositório de organizações não inicializado.")
        return self._organizations

    @property
    def agreements(self) -> PartnerAgreementRepository:
        """Repositório de convênios."""
        if self._agreements is None:
            raise RuntimeError("Repositório de convênios não inicializado.")
        return self._agreements

    @property
    def memberships(self) -> MembershipRepository:
        """Repositório de vínculos."""
        if self._memberships is None:
            raise RuntimeError("Repositório de vínculos não inicializado.")
        return self._memberships

    @property
    def module_entitlements(self) -> ModuleEntitlementRepository:
        """Repositório de entitlements de módulo."""
        if self._module_entitlements is None:
            raise RuntimeError("Repositório de entitlements não inicializado.")
        return self._module_entitlements

    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self._organizations = OrganizationRepository(self._session)
        self._agreements = PartnerAgreementRepository(self._session)
        self._memberships = MembershipRepository(self._session)
        self._module_entitlements = ModuleEntitlementRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await super().__aexit__(exc_type, exc_val, exc_tb)
        self._organizations = None
        self._agreements = None
        self._memberships = None
        self._module_entitlements = None
