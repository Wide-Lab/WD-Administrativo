from src.core.pagination.params import Page, PageParams
from src.modules.frota.application.dtos.filters import VehicleFilters
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import Vehicle


class ListVehiclesUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        page_params: PageParams,
        filters: VehicleFilters | None = None,
    ) -> Page[Vehicle]:
        """Os veículos da Empresa ativa, paginados.

        Veículo `inactive` continua na lista: ele some da escolha na tela, não do sistema — e
        segue nos relatórios do período em que rodou. Quem quiser só os ativos filtra."""

        async with self._uow as uow:
            return await uow.vehicles.paginate(page_params=page_params, filters=filters)
