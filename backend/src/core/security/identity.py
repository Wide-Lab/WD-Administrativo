import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import SessionDep

type UserId = uuid.UUID


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Identidade global de quem fez a requisição. Só identidade: sem organização, sem papel
    e sem permissão — isso muda a cada request e é resolvido pelo `access` (specs 04/05)."""

    id: UserId
    email: str
    name: str


class UserReader(Protocol):
    """Porta de leitura de identidade. Existe para o `core` resolver `current_user` sem
    importar `auth` — quem a implementa é o módulo `auth`, que é dono da tabela `users`."""

    async def get_active_by_id(self, user_id: UserId) -> CurrentUser | None: ...


class Authenticator[CredentialsT](Protocol):
    """Porta de autenticação: troca credenciais por uma identidade local.

    `PasswordAuthenticator` (spec 02) confere a senha na tabela `users`. Ligar "entrar com a
    Widelab" no futuro é somar um `CentralSsoAuthenticator` que valida o JWT da Central e
    mapeia pro usuário local — sem tocar em nada de `access`/autorização."""

    async def authenticate(self, credentials: CredentialsT) -> UserId: ...


type UserReaderFactory = Callable[[AsyncSession], UserReader]

_user_reader_factory: UserReaderFactory | None = None


def set_user_reader_factory(factory: UserReaderFactory) -> None:
    """Liga a implementação de `UserReader` ao `core`. Chamada uma vez em `mount_routes` pelo
    kernel — é o que mantém a seta de dependência apontando pra dentro (`core` nunca importa
    um módulo)."""

    global _user_reader_factory
    _user_reader_factory = factory


async def get_user_reader(session: SessionDep) -> UserReader:
    if _user_reader_factory is None:
        raise RuntimeError(
            "Nenhum UserReader registrado. O kernel `auth` deve chamar "
            "set_user_reader_factory() em mount_routes."
        )
    return _user_reader_factory(session)


UserReaderDep = Annotated[UserReader, Depends(get_user_reader)]
