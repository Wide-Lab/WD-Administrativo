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


_default_hasher = Argon2PasswordHasher()


def hash_password(plain: str) -> str:
    """Gera o hash Argon2id de uma senha."""

    return _default_hasher.hash(plain)


def verify_password(plain: str, hashed: str | None) -> bool:
    """Confere uma senha contra o hash. `hashed` é nulo enquanto o usuário não definiu senha
    (convidado, ou identidade só via SSO futuro) — nesse caso não há senha a conferir."""

    if hashed is None:
        return False
    return _default_hasher.verify(plain, hashed)
