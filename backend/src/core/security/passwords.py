from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

_hasher = PasswordHasher()


class Argon2PasswordHasher:
    """Hasher de senha com Argon2id (decisão travada na visão geral: nunca bcrypt)."""

    def hash(self, plain: str) -> str:
        """Gera um hash Argon2id da senha em texto plano."""

        return _hasher.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        """Verifica se a senha em texto plano corresponde ao hash. Retorna `False` em vez de
        levantar quando não corresponde ou o hash é inválido."""

        try:
            return _hasher.verify(hashed, plain)
        except VerifyMismatchError, VerificationError, InvalidHashError:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Indica se o hash deve ser regerado (parâmetros do Argon2 mudaram)."""

        return _hasher.check_needs_rehash(hashed)
