import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request, Response

from src.core.config import get_config
from src.core.exceptions import UnauthorizedError
from src.core.security.identity import CurrentUser, UserId, UserReaderDep
from src.core.security.startup import get_jwt_encoder


def issue_session(user_id: UserId) -> str:
    """Emite o JWT de sessão. O payload carrega só `sub` e `exp` — nunca papel nem
    organização: isso muda a cada request e é resolvido pelo `access`."""

    config = get_config()
    expires_at = datetime.now(UTC) + timedelta(hours=config.SESSION_TTL_HOURS)
    return get_jwt_encoder().encode({"sub": str(user_id), "exp": expires_at})


def read_session(token: str) -> UserId:
    """Valida o JWT de sessão e devolve o id do usuário. Levanta `UnauthorizedError` se o
    token for inválido ou estiver expirado."""

    claims = get_jwt_encoder().decode(token)
    try:
        return uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Sessão inválida.") from exc


def set_session_cookie(response: Response, token: str) -> None:
    """Entrega a sessão num cookie httpOnly (Secure e SameSite=Lax por padrão)."""

    config = get_config()
    response.set_cookie(
        key=config.SESSION_COOKIE_NAME,
        value=token,
        max_age=config.SESSION_TTL_HOURS * 3600,
        httponly=True,
        secure=config.SESSION_COOKIE_SECURE,
        samesite=config.SESSION_COOKIE_SAMESITE,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Apaga o cookie de sessão. Os atributos precisam bater com os do `set_cookie`, senão o
    navegador não encontra o cookie a apagar."""

    config = get_config()
    response.delete_cookie(
        key=config.SESSION_COOKIE_NAME,
        httponly=True,
        secure=config.SESSION_COOKIE_SECURE,
        samesite=config.SESSION_COOKIE_SAMESITE,
        path="/",
    )


async def current_user(request: Request, reader: UserReaderDep) -> CurrentUser:
    """Dependency de identidade: lê o cookie, valida a sessão e devolve o usuário; 401 se
    ausente, inválida, ou se o usuário sumiu/foi desativado desde a emissão do token.

    Mora no `core` justamente pra os módulos de negócio a consumirem sem importar `auth`."""

    token = request.cookies.get(get_config().SESSION_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Sessão ausente.")

    user = await reader.get_active_by_id(read_session(token))
    if user is None:
        raise UnauthorizedError("Sessão inválida.")

    return user


CurrentUserDep = Annotated[CurrentUser, Depends(current_user)]
