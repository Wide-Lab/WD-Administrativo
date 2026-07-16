from src.core.pagination.params import Page, PageParams
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.dtos.filters import MembershipFilters
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import Membership


class ListMembersUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de listagem de membros.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        page_params: PageParams,
    ) -> Page[Membership]:
        """
        Lista os membros da organização do path.

        Escopado pela organização ativa e não por quem pergunta: o filtro por
        `organization.id` é o que impede um admin de uma Empresa de enxergar o quadro de
        outra. Inclui os vínculos desativados — quem administra membros precisa ver quem foi
        desligado pra poder reativar.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            page_params (PageParams):
                Paginação.

        Returns:
            Page[Membership]:
                Os vínculos da organização.
        """

        async with self._uow as uow:
            return await uow.memberships.paginate(
                page_params=page_params,
                filters=MembershipFilters(organization_id=organization.id),
            )
