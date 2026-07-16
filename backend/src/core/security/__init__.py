"""Superfície de segurança do `core`.

É daqui que qualquer módulo — de kernel ou de negócio — consome identidade e sessão, sem
nunca importar `auth`."""

from src.core.security.identity import (
    Authenticator,
    CurrentUser,
    UserId,
    UserReader,
    set_user_reader_factory,
)
from src.core.security.passwords import hash_password, verify_password
from src.core.security.session import (
    CurrentUserDep,
    clear_session_cookie,
    current_user,
    issue_session,
    read_session,
    set_session_cookie,
)

__all__ = [
    "Authenticator",
    "CurrentUser",
    "CurrentUserDep",
    "UserId",
    "UserReader",
    "clear_session_cookie",
    "current_user",
    "hash_password",
    "issue_session",
    "read_session",
    "set_session_cookie",
    "set_user_reader_factory",
    "verify_password",
]
