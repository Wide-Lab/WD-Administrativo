import uuid

from src.core.exceptions import NotFoundError
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import Organization


class GetOrganizationUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de detalhe de organização.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(self, organization_id: uuid.UUID) -> Organization:
        """
        Detalha uma organização.

        Quem pode vê-la já foi decidido antes daqui, por `current_organization` — o use case
        recebe um id que a requisição comprovadamente alcança.

        Args:
            organization_id (uuid.UUID):
                A organização ativa da requisição.

        Returns:
            Organization:
                A organização.

        Raises:
            NotFoundError:
                Se a organização não existir.
        """

        async with self._uow as uow:
            organization = await uow.organizations.get_by_id_or_none(organization_id)
            if organization is None:
                raise NotFoundError("Organização não encontrada.")
            return organization
