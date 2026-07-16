import uuid

from src.core.exceptions import NotFoundError, ValidationAppError
from src.core.tenancy import CurrentOrganization
from src.core.types import UNSET
from src.modules.access.application.dtos.commands import UpdateMembershipCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import Membership, UpdateMembership
from src.modules.access.domain.permissions import is_role_valid_for, roles_for


class UpdateMembershipUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de mudança de papel/status de um membro.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        membership_id: uuid.UUID,
        command: UpdateMembershipCommand,
    ) -> Membership:
        """
        Muda o papel e/ou o status de um vínculo da organização do path.

        A conferência de papel×tipo aqui existe pra devolver 422 legível, **não** pra garantir
        a integridade: quem garante é o `CHECK` de `memberships`, ancorado pela FK composta
        contra `organizations(id, type)` — um `UPDATE` que passe por fora desta aplicação
        falha do mesmo jeito. Mesma divisão de trabalho do convênio (spec 03).

        Um vínculo de outra organização responde 404, não 403 — quem não pode vê-lo também não
        deveria descobrir que ele existe. Mesma escolha do `PATCH /convenios/{id}`.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            membership_id (uuid.UUID):
                O vínculo a atualizar.
            command (UpdateMembershipCommand):
                O novo papel e/ou status.

        Returns:
            Membership:
                O vínculo atualizado.

        Raises:
            NotFoundError:
                Se o vínculo não existir ou não pertencer à organização ativa.
            ValidationAppError:
                Se o papel não existir no tipo desta organização, ou se o corpo não pedir
                mudança nenhuma.
        """

        if command.role is None and command.status is None:
            raise ValidationAppError("Informe ao menos um campo para atualizar.")

        if command.role is not None and not is_role_valid_for(organization.type, command.role):
            valid = ", ".join(sorted(role.value for role in roles_for(organization.type)))
            raise ValidationAppError(
                f"O papel '{command.role.value}' não existe numa organização do tipo "
                f"'{organization.type.value}'. Papéis válidos: {valid}."
            )

        async with self._uow as uow:
            membership = await uow.memberships.get_by_id_or_none(membership_id)
            if membership is None or membership.organization_id != organization.id:
                raise NotFoundError("Vínculo não encontrado.")

            updated = await uow.memberships.update(
                membership_id,
                UpdateMembership(
                    role=command.role if command.role is not None else UNSET,
                    status=command.status if command.status is not None else UNSET,
                ),
            )
            await uow.commit()
            return updated
