import uuid

from src.core.exceptions import ConflictError, NotFoundError
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import InvitationStatus


class RevokeInvitationUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de revogação de convite.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        invitation_id: uuid.UUID,
    ) -> None:
        """
        Revoga um convite da organização do path, gravando `status = 'revoked'`.

        **A escrita vem primeiro, e a leitura só explica o que já aconteceu.** Esta ordem é a
        decisão central deste use case: o `UPDATE ... WHERE id AND organization_id AND status =
        'pending'` é quem decide, e ele decide no banco. Ler antes pra depois escrever abriria
        a janela clássica — dois `DELETE` simultâneos passariam os dois pela checagem, e um
        `DELETE` competindo com o aceite gravaria `revoked` por cima de um vínculo que já
        nasceu. Aqui o segundo recebe `False` e vai *perguntar* o porquê, sem poder de escrita
        nenhum. Mesma forma do `mark_accepted_if_pending` (spec 06).

        Revogar é **terminal**, e é por isso que a rota é `DELETE` e não um `PATCH` espelhando
        suspender/reativar convênio: um convite revogado não reativa — reconvidar é criar
        outro, com token novo.

        Os estados e o que cada um responde:

        - `pending` (inclusive o vencido, cuja coluna é `pending`) — grava `revoked`, 204.
        - `revoked` — 204, idempotente: o `DELETE` afirma um estado, e ele já é esse.
        - `accepted` — **409**. Um convite aceito virou membro, e revogá-lo não removeria o
          acesso: responderia sucesso e não faria nada do que quem chamou queria. Tirar acesso
          é `PATCH .../membros/{id}` (spec 04), que é `members.write`.
        - de outra organização, ou inexistente — **404**, nunca 403. Um 403 confirmaria que o
          convite existe, e a resposta não pode virar oráculo. Mesma escolha do
          `UpdateMembershipUseCase`.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            invitation_id (uuid.UUID):
                O convite a revogar. Por id, nunca por token — o token quem convidou não tem,
                nem deve ter.

        Raises:
            NotFoundError:
                Se o convite não existir ou não pertencer à organização ativa.
            ConflictError:
                Se o convite já tiver sido aceito.
        """

        async with self._uow as uow:
            revogado = await uow.invitations.mark_revoked_if_pending(
                invitation_id,
                organization.id,
            )
            if revogado:
                await uow.commit()
                return

            # Não revogamos: ou o convite não é desta organização, ou não estava pendente. A
            # leitura abaixo é diagnóstico — ela escolhe a resposta, não o efeito, que já foi
            # decidido (por não ter acontecido) lá em cima.
            invitation = await uow.invitations.get_by_id_or_none(invitation_id)
            if invitation is None or invitation.organization_id != organization.id:
                raise NotFoundError("Convite não encontrado.")

            if invitation.status is InvitationStatus.ACCEPTED:
                raise ConflictError(
                    "Este convite já foi aceito e virou um vínculo. Para retirar o acesso, "
                    "desative o membro."
                )
