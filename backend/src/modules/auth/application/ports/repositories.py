import uuid
from typing import Protocol

from src.modules.auth.domain.entities import Credentials, NewUser, UpdateUser, User


class UserRepositoryProtocol(Protocol):
    """Contrato do repositório de usuários consumido pelos use cases de `auth`."""

    async def get_credentials_by_email(
        self,
        email: str,
    ) -> Credentials | None: ...

    async def get_credentials_by_id(
        self,
        id_: uuid.UUID,
    ) -> Credentials | None: ...

    async def create(
        self,
        create_command: NewUser,
    ) -> User: ...

    async def update(
        self,
        id_: uuid.UUID,
        update_command: UpdateUser,
    ) -> User: ...
