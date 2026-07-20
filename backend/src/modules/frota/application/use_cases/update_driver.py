import uuid

from src.core.exceptions import NotFoundError, ValidationAppError
from src.core.types import UNSET
from src.modules.frota.application.dtos.commands import UpdateDriverCommand
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import Driver, UpdateDriver


class UpdateDriverUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        driver_id: uuid.UUID,
        command: UpdateDriverCommand,
    ) -> Driver:
        """Edita um condutor — inclusive desativá-lo, que é como alguém sai da lista.

        **Não há `DELETE` de condutor**, pelo mesmo motivo do veículo: as viagens que ele rodou
        são o produto. Desativar é `status=inactive`.

        Raises:
            NotFoundError:
                Se o condutor não existir nesta Empresa.
            ValidationAppError:
                Se o corpo não pedir mudança nenhuma.
            ConflictError:
                Se o `user_id` novo já for condutor nesta Empresa.
        """

        values = (
            command.name,
            command.user_id,
            command.license_number,
            command.license_category,
            command.license_expires_at,
            command.status,
        )
        if all(value is None for value in values):
            raise ValidationAppError("Informe ao menos um campo para atualizar.")

        async with self._uow as uow:
            if await uow.drivers.get_by_id_or_none(driver_id) is None:
                raise NotFoundError("Condutor não encontrado.")

            driver = await uow.drivers.update(
                driver_id,
                UpdateDriver(
                    name=command.name if command.name is not None else UNSET,
                    user_id=command.user_id if command.user_id is not None else UNSET,
                    license_number=(
                        command.license_number if command.license_number is not None else UNSET
                    ),
                    license_category=(
                        command.license_category if command.license_category is not None else UNSET
                    ),
                    license_expires_at=(
                        command.license_expires_at
                        if command.license_expires_at is not None
                        else UNSET
                    ),
                    status=command.status if command.status is not None else UNSET,
                ),
            )
            await uow.commit()
            return driver
