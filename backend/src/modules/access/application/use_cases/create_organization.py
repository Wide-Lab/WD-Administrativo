from src.modules.access.application.dtos.commands import CreateOrganizationCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import NewOrganization, Organization


class CreateOrganizationUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de criação de organização.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`. Recebe a implementação por `Depends` — o use
                case fala com a porta, nunca com o adapter.
        """

        self._uow = uow

    async def execute(self, command: CreateOrganizationCommand) -> Organization:
        """
        Provisiona um tenant: uma Empresa ou um Parceiro.

        O `type` é gravado aqui e nunca mais muda — não há use case de troca de tipo, e
        `UpdateOrganization` sequer tem o campo.

        Args:
            command (CreateOrganizationCommand):
                Tipo, nome e documento da organização.

        Returns:
            Organization:
                A organização criada.
        """

        async with self._uow as uow:
            organization = await uow.organizations.create(
                NewOrganization(
                    type=command.type,
                    name=command.name,
                    document=command.document,
                )
            )
            await uow.commit()
            return organization
