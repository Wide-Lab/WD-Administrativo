import logging
from collections.abc import Mapping
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from src.core.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)


class JwtTokenEncoder:
    """Encoder/decoder de token JWT com PyJWT (decisão travada: pyjwt, não python-jose).

    A sessão é assinada pela própria aplicação (HS256 por padrão — há um único verificador,
    ver `backend/02-identidade-e-sessao.md`)."""

    def __init__(self, secret_key: str, algorithm: str = "HS256") -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm

    def encode(self, payload: Mapping[str, Any]) -> str:
        """Assina um token JWT com os claims fornecidos."""

        return jwt.encode(dict(payload), self._secret_key, algorithm=self._algorithm)

    def decode(self, token: str) -> Mapping[str, Any]:
        """Valida e decodifica um token JWT. Levanta `UnauthorizedError` se expirado ou
        inválido."""

        try:
            return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except ExpiredSignatureError as exc:
            raise UnauthorizedError("Token expired.") from exc
        except InvalidTokenError as exc:
            logger.warning("Invalid token.", exc_info=True)
            raise UnauthorizedError("Invalid token.") from exc
