import uuid

from src.core.exceptions import NotFoundError
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.dtos.commands import UpdateAgreementStatusCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import PartnerAgreement, UpdatePartnerAgreement


class UpdateAgreementStatusUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de suspensão/reativação de convênio.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        agreement_id: uuid.UUID,
        command: UpdateAgreementStatusCommand,
    ) -> PartnerAgreement:
        """
        Suspende ou reativa um convênio da Empresa ativa.

        Quem suspende é a Empresa: o convênio precisa ser dela, e não bastar que ela apareça
        em algum dos lados. Um convênio de outra Empresa responde 404, não 403 — quem não
        pode vê-lo também não deveria descobrir que ele existe.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            agreement_id (uuid.UUID):
                O convênio a atualizar.
            command (UpdateAgreementStatusCommand):
                O novo status.

        Returns:
            PartnerAgreement:
                O convênio atualizado.

        Raises:
            NotFoundError:
                Se o convênio não existir ou não pertencer à Empresa ativa.
        """

        async with self._uow as uow:
            agreement = await uow.agreements.get_by_id_or_none(agreement_id)
            if agreement is None or agreement.company_id != organization.id:
                raise NotFoundError("Convênio não encontrado.")

            updated = await uow.agreements.update(
                agreement_id,
                UpdatePartnerAgreement(status=command.status),
            )
            await uow.commit()
            return updated
