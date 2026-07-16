import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import UserId
from src.core.tenancy.context import CurrentOrganization, OrganizationId
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import OrganizationStatus


class SqlAlchemyOrganizationReader:
    """Implementação da porta `OrganizationReader` do `core`.

    É por aqui que o `core` resolve `current_organization` sem importar `access`: o módulo
    entrega a implementação em `mount_routes`, e a seta de dependência segue apontando pra
    dentro. Mesmo padrão do `SqlAlchemyUserReader` (spec 02).

    **O vínculo ainda não é conferido — e isso é dívida conhecida, não esquecimento.** A
    spec 03 diz que `get_accessible` deve devolver `None` (→ 403) quando o usuário não tem
    vínculo com a organização, e afrouxar pra `platform_admin`. Só que vínculo é
    `memberships`, tabela da spec 04, e papel também: nenhum dos dois existe no schema ainda.
    A spec 03 previu exatamente isto — "esta spec pode subir com o guard ainda permissivo e
    apertar quando a 04 entrar".

    Enquanto a 04 não entra, qualquer usuário **autenticado** alcança qualquer organização
    **ativa**. O guard em si já é real: o 401 sem sessão e o 403 de organização inexistente ou
    desativada valem hoje. Apertar é trocar o corpo deste método por uma consulta a
    `memberships` — nenhuma rota, nenhum use case e nada do `core` muda junto."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_accessible(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> CurrentOrganization | None:
        """Devolve a organização ativa que o usuário pode acessar; `None` vira 403.

        TODO(spec 04): conferir o vínculo de `user_id` em `memberships` — e afrouxar pra
        `platform_admin`, que alcança qualquer `orgId`."""

        result = await self._session.execute(
            sa.select(OrganizationModel).where(
                OrganizationModel.id == organization_id,
                OrganizationModel.status == OrganizationStatus.ACTIVE,
            )
        )
        row = result.scalars().one_or_none()
        if row is None:
            return None

        return CurrentOrganization(id=row.id, type=row.type, name=row.name)
