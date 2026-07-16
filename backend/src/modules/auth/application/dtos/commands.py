from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoginCommand:
    """Comando de aplicação para autenticar um usuário."""

    email: str
    password: str


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    """Comando de aplicação para trocar a senha de um usuário logado."""

    current_password: str
    new_password: str
