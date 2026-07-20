from src.modules.frota.application.dtos.commands import CreateVehicleCommand
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import NewVehicle, Vehicle
from src.modules.frota.domain.rules import normalize_plate


class CreateVehicleUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, command: CreateVehicleCommand) -> Vehicle:
        """Cadastra um veículo na Empresa ativa.

        A placa é normalizada antes de gravar — é o que faz o `UNIQUE (organization_id, plate)`
        significar o que promete. A duplicata vira 409, e quem a detecta é o banco, não um
        `SELECT` antes: entre a leitura e a escrita cabe outro cadastro.

        Returns:
            Vehicle:
                O veículo criado.

        Raises:
            ConflictError:
                Se a placa já existir nesta Empresa.
        """

        async with self._uow as uow:
            vehicle = await uow.vehicles.create(
                NewVehicle(
                    plate=normalize_plate(command.plate),
                    brand=command.brand,
                    model=command.model,
                    model_year=command.model_year,
                    initial_odometer=command.initial_odometer,
                    status=command.status,
                )
            )
            await uow.commit()
            return vehicle
