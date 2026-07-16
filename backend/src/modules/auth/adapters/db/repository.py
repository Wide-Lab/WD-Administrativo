import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.modules.auth.adapters.db.models import User as UserModel
from src.modules.auth.domain.entities import Credentials, NewUser, UpdateUser, User


class UserRepository:
    """Repositório de usuários. Devolve entidades de domínio — o model SQLAlchemy nunca
    atravessa a fronteira do módulo."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_credentials_by_email(self, email: str) -> Credentials | None:
        """Obtém as credenciais de um usuário pelo e-mail. `None` se não encontrado.

        A comparação é case-insensitive porque a coluna é CITEXT — não há `.lower()` aqui."""

        row = await self._get_model_by(UserModel.email == email)
        return self._to_credentials(row) if row else None

    async def get_credentials_by_id(self, id_: uuid.UUID) -> Credentials | None:
        """Obtém as credenciais de um usuário pelo id. `None` se não encontrado."""

        row = await self._get_model_by(UserModel.id == id_)
        return self._to_credentials(row) if row else None

    async def create(self, create_command: NewUser) -> User:
        """Cria um usuário. O `commit` é do chamador, via unit of work."""

        model = UserModel(**create_command.to_dict())
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, id_: uuid.UUID, update_command: UpdateUser) -> User:
        """Atualiza os campos informados de um usuário. O `commit` é do chamador."""

        model = await self._get_model_by(UserModel.id == id_)
        if model is None:
            raise NotFoundError("Usuário não encontrado.")

        for field, value in update_command.defined_values().items():
            setattr(model, field, value)

        await self._session.flush()
        return self._to_entity(model)

    async def _get_model_by(self, condition: sa.ColumnElement[bool]) -> UserModel | None:
        result = await self._session.execute(sa.select(UserModel).where(condition))
        return result.scalars().one_or_none()

    def _to_credentials(self, row: UserModel) -> Credentials:
        return Credentials(
            id=row.id,
            password_hash=row.password_hash,
            status=row.status,
        )

    def _to_entity(self, row: UserModel) -> User:
        return User(
            id=row.id,
            email=row.email,
            name=row.name,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
