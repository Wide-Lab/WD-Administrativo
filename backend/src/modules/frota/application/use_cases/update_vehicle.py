import uuid

from src.core.exceptions import NotFoundError, ValidationAppError
from src.core.types import UNSET
from src.modules.frota.application.dtos.commands import UpdateVehicleCommand
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import UpdateVehicle, Vehicle
from src.modules.frota.domain.rules import normalize_plate


class UpdateVehicleUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        vehicle_id: uuid.UUID,
        command: UpdateVehicleCommand,
    ) -> Vehicle:
        """Edita um veículo — inclusive desativá-lo (`status`), que é como um carro sai da frota.

        **Não há `DELETE` de veículo**: apagar levaria junto o histórico, que é o produto. Um
        carro vendido vira `inactive`, some da lista de escolha e continua nos relatórios de
        quando rodava.

        Raises:
            NotFoundError:
                Se o veículo não existir nesta Empresa.
            ValidationAppError:
                Se o corpo não pedir mudança nenhuma.
            ConflictError:
                Se a placa nova já existir nesta Empresa.
        """

        values = (
            command.plate,
            command.brand,
            command.model,
            command.model_year,
            command.initial_odometer,
            command.status,
        )
        if all(value is None for value in values):
            raise ValidationAppError("Informe ao menos um campo para atualizar.")

        async with self._uow as uow:
            if await uow.vehicles.get_by_id_or_none(vehicle_id) is None:
                raise NotFoundError("Veículo não encontrado.")

            vehicle = await uow.vehicles.update(
                vehicle_id,
                UpdateVehicle(
                    plate=normalize_plate(command.plate) if command.plate is not None else UNSET,
                    brand=command.brand if command.brand is not None else UNSET,
                    model=command.model if command.model is not None else UNSET,
                    model_year=command.model_year if command.model_year is not None else UNSET,
                    initial_odometer=(
                        command.initial_odometer if command.initial_odometer is not None else UNSET
                    ),
                    status=command.status if command.status is not None else UNSET,
                ),
            )
            await uow.commit()
            return vehicle
