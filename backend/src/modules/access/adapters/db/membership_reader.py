from sqlalchemy.ext.asyncio import AsyncSession

from src.core.authz import Permission
from src.core.security import UserId
from src.core.tenancy import OrganizationId
from src.modules.access.adapters.db.repository import MembershipRepository
from src.modules.access.domain.entities import Role
from src.modules.access.domain.permissions import permissions_for


class SqlAlchemyMembershipReader:
    """Implementação da porta `PermissionReader` do `core`.

    É por aqui que o `core` resolve `require_permission` sem importar `access`: o módulo
    entrega a implementação em `mount_routes`. Mesmo padrão do `SqlAlchemyUserReader`
    (spec 02) e do `SqlAlchemyOrganizationReader` (spec 03).

    Não repete SQL: delega ao `MembershipRepository` e põe por cima o mapa papel→permissões.
    O que ele acrescenta é a **tradução** — o `core` pergunta por capability, o `access`
    responde a partir de papel, e o `core` nunca fica sabendo que papel existe."""

    def __init__(self, session: AsyncSession) -> None:
        self._memberships = MembershipRepository(session)

    async def get_role(self, user_id: UserId, organization_id: OrganizationId) -> Role | None:
        """O papel ativo de `user_id` em `organization_id`; `None` se não houver vínculo."""

        membership = await self._memberships.get_active_for_user_and_organization(
            user_id=user_id,
            organization_id=organization_id,
        )
        return membership.role if membership is not None else None

    async def is_platform_admin(self, user_id: UserId) -> bool:
        """Se `user_id` é admin da plataforma — alcança qualquer tenant."""

        return await self._memberships.is_platform_admin(user_id)

    async def get_permissions(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> frozenset[Permission]:
        """As permissões de `user_id` dentro de `organization_id`. Vazio se não houver vínculo
        — e vazio faz `require_permission` negar com 403.

        As duas fontes se somam: o papel na organização e, se for o caso, o `platform_admin`.
        A soma é o que faz a linha `PATCH /membros/{id}` da spec (`company_admin` **ou**
        `platform_admin`) valer sem um `if` na rota — a plataforma conserta o vínculo de uma
        Empresa onde ela própria não tem vínculo nenhum."""

        granted: set[Permission] = set()

        role = await self.get_role(user_id=user_id, organization_id=organization_id)
        if role is not None:
            granted |= permissions_for(role)

        if await self.is_platform_admin(user_id):
            granted |= permissions_for(Role.PLATFORM_ADMIN)

        return frozenset(granted)
