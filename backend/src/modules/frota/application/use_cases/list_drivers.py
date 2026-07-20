from src.core.pagination.params import Page, PageParams
from src.modules.frota.application.dtos.filters import DriverFilters
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import Driver


class ListDriversUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        page_params: PageParams,
        filters: DriverFilters | None = None,
    ) -> Page[Driver]:
        """Os condutores da Empresa ativa, paginados.

        Exige `frota.drivers.read`, que o `collaborator` **não** tem: ele lança em nome de si
        mesmo, e a lista de condutores da Empresa não é dele."""

        async with self._uow as uow:
            return await uow.drivers.paginate(page_params=page_params, filters=filters)
