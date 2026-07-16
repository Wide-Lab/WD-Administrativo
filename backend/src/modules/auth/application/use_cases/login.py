from src.core.security import Authenticator, UserId
from src.modules.auth.application.dtos.commands import LoginCommand
from src.modules.auth.domain.entities import PasswordCredentials


class LoginUseCase:
    def __init__(self, authenticator: Authenticator[PasswordCredentials]) -> None:
        """
        Inicializa o use case de login.

        Args:
            authenticator (Authenticator[PasswordCredentials]):
                Porta de autenticação. Recebe a implementação por `Depends` — trocar
                `PasswordAuthenticator` por outra não mexe aqui.
        """

        self._authenticator = authenticator

    async def execute(self, command: LoginCommand) -> UserId:
        """
        Autentica um usuário pelas credenciais e devolve sua identidade.

        Quem emite a sessão é o adapter HTTP — o use case não sabe o que é cookie.

        Args:
            command (LoginCommand):
                E-mail e senha informados.

        Raises:
            UnauthorizedError:
                Se as credenciais forem inválidas ou o usuário estiver desativado.
        """

        return await self._authenticator.authenticate(
            PasswordCredentials(email=command.email, password=command.password)
        )
