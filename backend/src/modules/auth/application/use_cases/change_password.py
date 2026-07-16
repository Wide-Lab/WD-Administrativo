from src.core.exceptions import UnauthorizedError
from src.core.security import UserId, hash_password, verify_password
from src.modules.auth.application.dtos.commands import ChangePasswordCommand
from src.modules.auth.application.ports.unit_of_work import AuthUnitOfWorkProtocol
from src.modules.auth.domain.entities import UpdateUser


class ChangePasswordUseCase:
    def __init__(self, uow: AuthUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de troca de senha.

        Args:
            uow (AuthUnitOfWorkProtocol):
                Unit of work de autenticação.
        """

        self._uow = uow

    async def execute(self, user_id: UserId, command: ChangePasswordCommand) -> None:
        """
        Troca a senha de um usuário já logado, conferindo a senha atual.

        Args:
            user_id (UserId):
                Usuário da sessão corrente.
            command (ChangePasswordCommand):
                Senha atual e nova senha.

        Raises:
            UnauthorizedError:
                Se a senha atual não conferir, ou se o usuário ainda não tem senha definida
                — nesse caso quem define a senha é o onboarding (spec 06), não esta rota.
        """

        async with self._uow as uow:
            credentials = await uow.users.get_credentials_by_id(user_id)

            if credentials is None or not verify_password(
                command.current_password, credentials.password_hash
            ):
                raise UnauthorizedError("Senha atual inválida.")

            await uow.users.update(
                user_id,
                UpdateUser(password_hash=hash_password(command.new_password)),
            )
            await uow.commit()
