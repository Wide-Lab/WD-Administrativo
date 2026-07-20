import uuid

from src.core.exceptions import NotFoundError
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import Driver


class GetDriverUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, driver_id: uuid.UUID) -> Driver:
        """Um condutor da Empresa ativa. Condutor de outra Empresa é 404, pelo escopo do
        repositório — não por um `if`.

        Raises:
            NotFoundError:
                Se o condutor não existir nesta Empresa.
        """

        async with self._uow as uow:
            driver = await uow.drivers.get_by_id_or_none(driver_id)
            if driver is None:
                raise NotFoundError("Condutor não encontrado.")
            return driver
