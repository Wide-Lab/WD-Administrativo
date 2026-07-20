import uuid

from src.core.exceptions import NotFoundError
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import Vehicle


class GetVehicleUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, vehicle_id: uuid.UUID) -> Vehicle:
        """Um veículo da Empresa ativa.

        Um `id` que existe mas é de **outra** Empresa responde 404, não 403 — e não por um `if`:
        o repositório é tenant-scoped e simplesmente não o encontra. A resposta não pode virar
        oráculo de que o veículo existe em algum lugar.

        Raises:
            NotFoundError:
                Se o veículo não existir nesta Empresa.
        """

        async with self._uow as uow:
            vehicle = await uow.vehicles.get_by_id_or_none(vehicle_id)
            if vehicle is None:
                raise NotFoundError("Veículo não encontrado.")
            return vehicle
