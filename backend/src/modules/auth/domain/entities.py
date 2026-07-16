import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from src.core.types import UNSET, BaseCreateCommand, BaseUpdateCommand, UnsetType


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class User:
    """Identidade global de uma pessoa: um e-mail, um login. Sem organização e sem papel —
    essas relações são do módulo `access` (specs 03/04)."""

    id: uuid.UUID
    email: str
    name: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Credentials:
    """O mínimo pra autenticar alguém. Nunca sai do módulo `auth`: o `password_hash` não
    atravessa a fronteira do módulo nem aparece em resposta.

    `password_hash` é nulo enquanto o convidado não definiu senha (spec 06), ou se a
    identidade vier só do SSO futuro."""

    id: uuid.UUID
    password_hash: str | None
    status: UserStatus

    @property
    def is_active(self) -> bool:
        return self.status is UserStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class PasswordCredentials:
    """O que o `PasswordAuthenticator` recebe. Um `CentralSsoAuthenticator` futuro receberia
    outro tipo de credencial — daí a porta `Authenticator` ser genérica."""

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class NewUser(BaseCreateCommand):
    email: str
    name: str
    password_hash: str | None = None
    status: UserStatus = UserStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateUser(BaseUpdateCommand):
    email: str | UnsetType = UNSET
    name: str | UnsetType = UNSET
    password_hash: str | None | UnsetType = UNSET
    status: UserStatus | UnsetType = UNSET
