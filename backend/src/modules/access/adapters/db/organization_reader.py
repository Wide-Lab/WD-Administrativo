import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import UserId
from src.core.tenancy.context import CurrentOrganization, OrganizationId
from src.modules.access.adapters.db.membership_reader import SqlAlchemyMembershipReader
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import OrganizationStatus


class SqlAlchemyOrganizationReader:
    """Implementação da porta `OrganizationReader` do `core`.

    É por aqui que o `core` resolve `current_organization` sem importar `access`: o módulo
    entrega a implementação em `mount_routes`, e a seta de dependência segue apontando pra
    dentro. Mesmo padrão do `SqlAlchemyUserReader` (spec 02).

    **O vínculo é conferido aqui — é este método que fecha o critério 2 da spec 03**, que
    subiu permissivo por dependência: vínculo é `memberships`, tabela da spec 04, e não havia
    o que consultar. Como a spec 03 previu ("apertar na 04 é trocar o corpo de um método"),
    apertar custou exatamente isto: uma consulta a mais, nenhuma rota e nenhum use case
    mudaram junto."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._memberships = SqlAlchemyMembershipReader(session)

    async def get_accessible(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> CurrentOrganization | None:
        """Devolve a organização ativa que o usuário pode acessar; `None` vira 403.

        Alcança quem tem vínculo ativo nela — e o `platform_admin`, que alcança qualquer
        `orgId` (a checagem afrouxada pra plataforma que a spec 03 pediu). Note que a
        organização precisa estar **ativa** nos dois casos: um tenant desativado não abre nem
        pra Widelab, senão "desativado" não significaria nada."""

        result = await self._session.execute(
            sa.select(OrganizationModel).where(
                OrganizationModel.id == organization_id,
                OrganizationModel.status == OrganizationStatus.ACTIVE,
            )
        )
        row = result.scalars().one_or_none()
        if row is None:
            return None

        has_membership = (
            await self._memberships.get_role(
                user_id=user_id,
                organization_id=organization_id,
            )
            is not None
        )
        if not has_membership and not await self._memberships.is_platform_admin(user_id):
            return None

        return CurrentOrganization(id=row.id, type=row.type, name=row.name)
