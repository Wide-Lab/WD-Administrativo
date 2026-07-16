from src.core.pagination.params import Page, PageParams
from src.modules.access.application.dtos.filters import OrganizationFilters
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import Organization


class ListOrganizationsUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de listagem de organizações.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        page_params: PageParams,
        filters: OrganizationFilters | None = None,
    ) -> Page[Organization]:
        """
        Lista os tenants. É visão de plataforma — não é escopada por organização.

        Args:
            page_params (PageParams):
                Paginação.
            filters (OrganizationFilters | None):
                Filtro opcional por tipo.

        Returns:
            Page[Organization]:
                A página de organizações.
        """

        async with self._uow as uow:
            return await uow.organizations.paginate(page_params=page_params, filters=filters)
