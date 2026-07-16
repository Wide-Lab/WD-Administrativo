from datetime import UTC, datetime

from src.core.exceptions import GoneError, NotFoundError
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import InvitationWithOrganization


class GetInvitationUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de leitura pública de convite.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(self, token: str) -> InvitationWithOrganization:
        """
        Os dados mínimos que a tela de aceite mostra: quem convidou, para qual e-mail, com
        qual papel.

        É **público** — quem vai aceitar ainda não tem sessão. O que autoriza a leitura é o
        próprio token, e é por isso que ele é opaco e de 32 bytes: adivinhar um é o único
        caminho para ler o convite de outra pessoa.

        A distinção entre 404 e 410 é deliberada, e não vaza nada que o portador do token já
        não saiba: **404** é "este token nunca existiu"; **410** é "existiu e não vale mais"
        — expirado, revogado ou já aceito. Sem ela, a tela não teria como dizer "seu convite
        expirou, peça outro" em vez de "link inválido".

        Args:
            token (str):
                O token opaco do convite.

        Returns:
            InvitationWithOrganization:
                O convite pendente e a organização que convidou.

        Raises:
            NotFoundError:
                Se o token não existir.
            GoneError:
                Se o convite não estiver mais aberto.
        """

        async with self._uow as uow:
            found = await uow.invitations.get_with_organization_by_token(token)
            if found is None:
                raise NotFoundError("Convite não encontrado.")

            if not found.invitation.is_open(datetime.now(UTC)):
                raise GoneError("Este convite não está mais válido.")

            return found
