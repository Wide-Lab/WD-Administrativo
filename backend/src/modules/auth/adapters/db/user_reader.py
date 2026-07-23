from collections.abc import Mapping, Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security.identity import CurrentUser, UserId, UserProfile
from src.modules.auth.adapters.db.models import User as UserModel
from src.modules.auth.domain.entities import UserStatus


class SqlAlchemyUserReader:
    """Implementação da porta `UserReader` do `core`.

    É por aqui que o `core` resolve `current_user` sem importar `auth`: o módulo entrega a
    implementação em `mount_routes`, e a seta de dependência segue apontando pra dentro."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_by_id(self, user_id: UserId) -> CurrentUser | None:
        """Devolve a identidade de um usuário ativo. `None` se ele não existe ou foi
        desativado — desativar alguém derruba o acesso na requisição seguinte, sem esperar o
        token expirar."""

        result = await self._session.execute(
            sa.select(UserModel).where(
                UserModel.id == user_id,
                UserModel.status == UserStatus.ACTIVE,
            )
        )
        row = result.scalars().one_or_none()
        if row is None:
            return None

        return CurrentUser(id=row.id, email=row.email, name=row.name)

    async def list_profiles_by_ids(
        self,
        user_ids: Sequence[UserId],
    ) -> Mapping[UserId, UserProfile]:
        """Nome e e-mail de um punhado de pessoas, num `SELECT` só.

        **Sem filtro por `status`**, ao contrário do `get_active_by_id` logo acima — e a
        diferença entre os dois é o ponto da porta: aquele decide quem entra, este só diz quem é
        o dono de um vínculo que já existe. Ver o docstring da porta.

        A lista vazia sai daqui sem tocar o banco: um `IN ()` seria SQL válido e inútil."""

        if not user_ids:
            return {}

        result = await self._session.execute(
            sa.select(UserModel).where(UserModel.id.in_(set(user_ids)))
        )

        return {
            row.id: UserProfile(id=row.id, email=row.email, name=row.name)
            for row in result.scalars()
        }
