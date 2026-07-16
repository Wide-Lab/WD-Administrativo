from datetime import UTC, datetime

from src.core.exceptions import GoneError, NotFoundError
from src.core.security import UserDirectory, UserId
from src.modules.access.application.dtos.commands import AcceptInvitationCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import NewMembership


def _name_from_email(email: str) -> str:
    """O nome de quem aceitou sem mandar um.

    Existe por causa da resposta uniforme: `name` é opcional no contrato, mas uma identidade
    nova precisa de nome. Exigi-lo só quando o usuário não existe responderia 422 exatamente
    nos e-mails sem conta — e o 422 viraria um oráculo de "esta pessoa já tem cadastro". O
    fallback é feio e trocável pela própria pessoa depois; o vazamento não seria."""

    return email.split("@", 1)[0]


class AcceptInvitationUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol, directory: UserDirectory) -> None:
        """
        Inicializa o use case de aceite de convite.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
            directory (UserDirectory):
                Porta de identidade. É por ela que o convidado ganha login — `access` não
                importa `auth`, e a sessão por trás dela é a mesma da uow, então o usuário e o
                vínculo nascem na mesma transação.
        """

        self._uow = uow
        self._directory = directory

    async def execute(self, command: AcceptInvitationCommand) -> UserId:
        """
        Aceita um convite: garante o login, cria o vínculo e gasta o token.

        **A senha só é usada se a pessoa ainda não tem conta.** Quem já tem login apenas ganha
        o vínculo, e a senha do corpo é ignorada — senão um convite viraria um caminho de
        troca de senha de conta alheia: bastaria convidar um e-mail existente para redefinir a
        senha de quem já usa o sistema. Os dois caminhos respondem igual, e é isso que cumpre
        a "resposta uniforme" da spec.

        Idempotência: o token é gasto por um `UPDATE` condicional, não por um `if` — dois
        aceites simultâneos do mesmo token não criam dois vínculos, e reaceitar um token já
        gasto responde 410 sem abrir sessão.

        Args:
            command (AcceptInvitationCommand):
                Token, senha e (opcionalmente) nome.

        Returns:
            UserId:
                Quem aceitou — é para ele que a rota emite a sessão.

        Raises:
            NotFoundError:
                Se o token não existir.
            GoneError:
                Se o convite estiver expirado, revogado ou já aceito.
            ConflictError:
                Se a pessoa já tiver vínculo com esta organização.
        """

        async with self._uow as uow:
            invitation = await uow.invitations.get_by_token_or_none(command.token)
            if invitation is None:
                raise NotFoundError("Convite não encontrado.")

            if not invitation.is_open(datetime.now(UTC)):
                raise GoneError("Este convite não está mais válido.")

            organization = await uow.organizations.get_by_id_or_none(invitation.organization_id)
            if organization is None:
                # A FK com `ondelete=CASCADE` torna isto inalcançável: sem a organização, não
                # há convite. Está aqui porque o tipo do repositório é honesto sobre o `None`.
                raise NotFoundError("Convite não encontrado.")

            # Gasta o token **antes** de criar qualquer coisa. Se o `UPDATE` não pegou a linha,
            # outra requisição chegou primeiro: sair aqui é o que impede o vínculo duplicado,
            # e o rollback desfaz o que já tivesse acontecido nesta transação.
            if not await uow.invitations.mark_accepted_if_pending(invitation.id):
                raise GoneError("Este convite não está mais válido.")

            user_id = await self._directory.find_id_by_email(invitation.email)
            if user_id is None:
                user_id = await self._directory.create(
                    email=invitation.email,
                    name=command.name or _name_from_email(invitation.email),
                    password=command.password,
                )

            await uow.memberships.create(
                NewMembership(
                    user_id=user_id,
                    organization_id=organization.id,
                    organization_type=organization.type,
                    role=invitation.role,
                )
            )

            await uow.commit()
            return user_id
