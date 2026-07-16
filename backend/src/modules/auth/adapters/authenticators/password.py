import logging

from src.core.exceptions import UnauthorizedError
from src.core.security import UserId, verify_password
from src.modules.auth.application.ports.unit_of_work import AuthUnitOfWorkProtocol
from src.modules.auth.domain.entities import PasswordCredentials

logger = logging.getLogger(__name__)


class PasswordAuthenticator:
    """Implementação da porta `Authenticator` desta spec: confere a senha na tabela `users`.

    Ligar "entrar com a Widelab" depois é somar um `CentralSsoAuthenticator` ao lado deste e
    trocar a linha de wiring em `dependencies.py` — nada fora do módulo `auth` muda."""

    def __init__(self, uow: AuthUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def authenticate(self, credentials: PasswordCredentials) -> UserId:
        """Troca e-mail + senha pelo id do usuário.

        Raises:
            UnauthorizedError:
                Se o e-mail não existe, a senha não confere, o usuário ainda não definiu
                senha, ou está desativado. A mensagem é sempre a mesma — distinguir os casos
                diria a um atacante quais e-mails existem.
        """

        async with self._uow as uow:
            found = await uow.users.get_credentials_by_email(credentials.email)

        password_matches = found is not None and verify_password(
            credentials.password, found.password_hash
        )
        if found is None or not password_matches or not found.is_active:
            logger.info("Tentativa de login recusada.")
            raise UnauthorizedError("Credenciais inválidas.")

        return found.id
