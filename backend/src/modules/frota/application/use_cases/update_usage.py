import uuid
from datetime import UTC, datetime

from src.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from src.core.types import UNSET
from src.modules.frota.application.dtos.commands import UpdateUsageCommand
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.application.usage_scope import UsageScope, resolve_writable_driver_id
from src.modules.frota.domain.entities import UpdateVehicleUsage, VehicleUsage
from src.modules.frota.domain.rules import is_future


class UpdateUsageUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        usage_id: uuid.UUID,
        command: UpdateUsageCommand,
        scope: UsageScope,
        user_id: uuid.UUID,
        now: datetime | None = None,
    ) -> VehicleUsage:
        """Corrige uma viagem — inclusive uma já encerrada, e isso é de propósito: painel
        trocado, hodômetro digitado errado e data trocada são casos reais, e o `PATCH` é onde eles
        se resolvem. Encerrar, esse, é a rota própria.

        Quem só tem `write_own` corrige exclusivamente as próprias viagens, e **não** pode
        transferi-las pra outro condutor.

        Raises:
            NotFoundError:
                Se a viagem não existir nesta Empresa.
            ForbiddenError:
                Se quem só tem `write_own` mexer na viagem de outro condutor.
            ValidationAppError:
                Se o corpo for vazio, se a data nova for futura, ou se o veículo/condutor novo
                não estiver ativo.
            ConflictError:
                Se a correção fizer o período se sobrepor a outra viagem do mesmo veículo.
        """

        now = now or datetime.now(UTC)

        values = (
            command.vehicle_id,
            command.driver_id,
            command.started_at,
            command.ended_at,
            command.start_odometer,
            command.end_odometer,
            command.purpose,
            command.notes,
        )
        if all(value is None for value in values):
            raise ValidationAppError("Informe ao menos um campo para atualizar.")

        if command.started_at is not None and is_future(command.started_at, now):
            raise ValidationAppError("A data de saída não pode estar no futuro.")

        async with self._uow as uow:
            usage = await uow.usages.get_by_id_or_none(usage_id)
            if usage is None:
                raise NotFoundError("Viagem não encontrada.")

            if not scope.can_write_any:
                own = await uow.drivers.get_by_user_id(user_id)
                if own is None or usage.driver_id != own.id:
                    raise ForbiddenError("Você só pode corrigir as suas próprias viagens.")

            driver_id: uuid.UUID | None = None
            if command.driver_id is not None:
                driver_id = await resolve_writable_driver_id(
                    scope=scope,
                    drivers=uow.drivers,
                    user_id=user_id,
                    requested_driver_id=command.driver_id,
                )
                driver = await uow.drivers.get_by_id_or_none(driver_id)
                if driver is None:
                    raise ValidationAppError("Condutor não encontrado nesta Empresa.")
                if not driver.accepts_new_usage:
                    raise ValidationAppError(
                        f"O condutor {driver.name} está inativo e não pode receber uma viagem."
                    )

            if command.vehicle_id is not None:
                vehicle = await uow.vehicles.get_by_id_or_none(command.vehicle_id)
                if vehicle is None:
                    raise ValidationAppError("Veículo não encontrado nesta Empresa.")
                if not vehicle.accepts_new_usage:
                    raise ValidationAppError(
                        f"O veículo {vehicle.plate} está '{vehicle.status.value}' e não pode "
                        "receber uma viagem."
                    )

            updated = await uow.usages.update(
                usage_id,
                UpdateVehicleUsage(
                    vehicle_id=command.vehicle_id if command.vehicle_id is not None else UNSET,
                    driver_id=driver_id if driver_id is not None else UNSET,
                    started_at=command.started_at if command.started_at is not None else UNSET,
                    ended_at=command.ended_at if command.ended_at is not None else UNSET,
                    start_odometer=(
                        command.start_odometer if command.start_odometer is not None else UNSET
                    ),
                    end_odometer=(
                        command.end_odometer if command.end_odometer is not None else UNSET
                    ),
                    purpose=command.purpose if command.purpose is not None else UNSET,
                    notes=command.notes if command.notes is not None else UNSET,
                ),
            )
            await uow.commit()
            return updated
