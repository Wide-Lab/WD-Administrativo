import secrets
from datetime import UTC, datetime, timedelta

from src.core.config import get_config
from src.core.exceptions import ValidationAppError
from src.core.notifications import EmailMessage, EmailSender
from src.core.security import CurrentUser
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.dtos.commands import CreateInvitationCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import Invitation, NewInvitation
from src.modules.access.domain.permissions import is_role_valid_for, roles_for

_TOKEN_BYTES = 32
"""32 bytes url-safe, como a spec pede. É credencial: quem tem o token aceita o convite."""


def _generate_token() -> str:
    return secrets.token_urlsafe(_TOKEN_BYTES)


class CreateInvitationUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol, email_sender: EmailSender) -> None:
        """
        Inicializa o use case de criação de convite.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
            email_sender (EmailSender):
                Porta de envio de e-mail. O provedor concreto é infra, não desta spec.
        """

        self._uow = uow
        self._email_sender = email_sender

    async def execute(
        self,
        organization: CurrentOrganization,
        invited_by: CurrentUser,
        command: CreateInvitationCommand,
    ) -> Invitation:
        """
        Convida alguém para a organização do path, com um papel já definido.

        O convite é sempre para a organização do path — nunca para outra. É isso, e não um
        `if`, que faz o critério 4 da spec valer: um `hr` que aponte para a organização alheia
        não passa do `require_permission`, porque a permissão é resolvida *naquele* `orgId`.

        A conferência de papel×tipo aqui existe pra devolver 422 legível; quem **garante** é o
        `CHECK` de `invitations`, ancorado pela FK composta.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada. É pra ela que o convite dá vínculo.
            invited_by (CurrentUser):
                Quem convidou. Convite é ato com responsável.
            command (CreateInvitationCommand):
                E-mail e papel do convidado.

        Returns:
            Invitation:
                O convite criado, pendente.

        Raises:
            ValidationAppError:
                Se o papel não existir no tipo desta organização.
        """

        if not is_role_valid_for(organization.type, command.role):
            valid = ", ".join(sorted(role.value for role in roles_for(organization.type)))
            raise ValidationAppError(
                f"O papel '{command.role.value}' não existe numa organização do tipo "
                f"'{organization.type.value}'. Papéis válidos: {valid}."
            )

        config = get_config()
        token = _generate_token()

        async with self._uow as uow:
            invitation = await uow.invitations.create(
                NewInvitation(
                    email=command.email,
                    organization_id=organization.id,
                    organization_type=organization.type,
                    role=command.role,
                    token=token,
                    expires_at=datetime.now(UTC) + timedelta(days=config.INVITATION_TTL_DAYS),
                    invited_by=invited_by.id,
                )
            )
            await uow.commit()

        # Depois do commit, de propósito: um e-mail que sai e uma transação que volta atrás
        # deixariam um token vivo no e-mail de alguém sem linha no banco. O contrário — commit
        # feito e e-mail que falha — é recuperável reenviando; este não é.
        await self._email_sender.send(
            EmailMessage(
                to=invitation.email,
                subject=f"Você foi convidado para {organization.name}",
                body=(
                    f"Você foi convidado para {organization.name} como "
                    f"{invitation.role.value}.\n\n"
                    f"Aceite em: {config.APP_BASE_URL}/convites/{invitation.token}\n\n"
                    f"O convite expira em {config.INVITATION_TTL_DAYS} dias."
                ),
            )
        )

        return invitation
