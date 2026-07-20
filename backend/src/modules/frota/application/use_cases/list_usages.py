import uuid
from dataclasses import replace

from src.core.pagination.params import Page, PageParams
from src.modules.frota.application.dtos.filters import VehicleUsageFilters
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.application.usage_scope import UsageScope
from src.modules.frota.domain.entities import VehicleUsage


class ListUsagesUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        page_params: PageParams,
        scope: UsageScope,
        user_id: uuid.UUID,
        filters: VehicleUsageFilters | None = None,
    ) -> Page[VehicleUsage]:
        """Os usos da Empresa ativa — **e o escopo é dado, não porta**.

        A rota exige só o módulo; o que ela devolve depende da capability. Quem tem
        `frota.usages.read` vê os usos de toda a Empresa; quem não tem vê só os do condutor
        vinculado ao próprio `user_id`, e uma lista vazia se não houver condutor vinculado.

        Uma rota só, e não duas: duplicá-la duplicaria paginação, filtros e ordenação pra mudar
        uma cláusula `WHERE`. O filtro `?condutor=` de quem não pode ler tudo é **sobrescrito**,
        não somado — pedir o condutor de outro não pode virar um jeito de vê-lo.
        """

        filters = filters or VehicleUsageFilters()

        async with self._uow as uow:
            if not scope.can_read_any:
                own = await uow.drivers.get_by_user_id(user_id)
                if own is None:
                    return Page(
                        items=[],
                        total=0,
                        page=page_params.page,
                        page_size=page_params.page_size,
                    )
                filters = replace(filters, driver_id=own.id)

            return await uow.usages.paginate(page_params=page_params, filters=filters)
