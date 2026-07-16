from sqlalchemy.ext.asyncio import AsyncSession

from src.core.modules import ModuleKey
from src.core.tenancy import OrganizationId
from src.modules.access.adapters.db.repository import ModuleEntitlementRepository


class SqlAlchemyModuleEntitlementReader:
    """Implementação da porta `ModuleEntitlementReader` do `core`.

    É por aqui que o `core` resolve `require_module` sem importar `access`: o módulo entrega a
    implementação em `mount_routes`. Mesmo padrão do `SqlAlchemyUserReader` (spec 02), do
    `SqlAlchemyOrganizationReader` (spec 03) e do `SqlAlchemyMembershipReader` (spec 04).

    Não repete SQL: delega ao `ModuleEntitlementRepository`. Aqui não há tradução nenhuma por
    cima — diferente do `PermissionReader`, que converte papel em capability, entitlement já é
    a resposta na forma que o `core` pergunta."""

    def __init__(self, session: AsyncSession) -> None:
        self._entitlements = ModuleEntitlementRepository(session)

    async def is_enabled(self, organization_id: OrganizationId, module_key: ModuleKey) -> bool:
        """Se a organização tem o módulo habilitado. Ausência de linha é o "não" — e é ele que
        faz `require_module` negar com 403."""

        entitlement = await self._entitlements.get_by_organization_and_module(
            organization_id=organization_id,
            module_key=module_key,
        )
        return entitlement is not None
