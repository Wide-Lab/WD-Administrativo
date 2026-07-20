import uuid
from datetime import UTC, datetime

from src.core.exceptions import ValidationAppError
from src.modules.frota.application.dtos.commands import CreateUsageCommand
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.application.usage_scope import UsageScope, resolve_writable_driver_id
from src.modules.frota.domain.entities import NewVehicleUsage, VehicleUsage
from src.modules.frota.domain.rules import is_future


class CreateUsageUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        command: CreateUsageCommand,
        scope: UsageScope,
        user_id: uuid.UUID,
        now: datetime | None = None,
    ) -> VehicleUsage:
        """Lança uma viagem — inclusive retroativa, que é o caso normal.

        As três validações abaixo existem porque **o banco não as alcança**: `now()` não entra em
        `CHECK`, e um `CHECK` não enxerga outra tabela. Tudo o mais é do banco — a sobreposição de
        período, os hodômetros, o par `ended_at`/`end_odometer` e o cruzamento de tenant.

        A sobreposição em particular **não** é verificada com um `SELECT` antes: entre a leitura e
        a escrita cabe outro lançamento, e a corrida é justamente o caso que a constraint de
        exclusão existe pra pegar. Ela sobe como `IntegrityError` e o repositório a traduz em 409.

        Args:
            command (CreateUsageCommand):
                O lançamento.
            scope (UsageScope):
                As capabilities de uso de quem chama.
            user_id (uuid.UUID):
                Quem está lançando — vira `created_by`, e resolve o "próprio" do `write_own`.
            now (datetime | None):
                O agora, injetável pra o teste não depender do relógio.

        Returns:
            VehicleUsage:
                A viagem registrada.

        Raises:
            ForbiddenError:
                Se quem só tem `write_own` lançar para outro condutor.
            ValidationAppError:
                Se a data for futura, se o veículo ou o condutor não estiverem ativos, ou se quem
                só tem `write_own` não for condutor.
            ConflictError:
                Se o período se sobrepuser a outra viagem do mesmo veículo.
        """

        now = now or datetime.now(UTC)

        if is_future(command.started_at, now):
            raise ValidationAppError(
                "A data de saída não pode estar no futuro. O sistema registra a viagem que "
                "aconteceu, não a que vai acontecer."
            )

        async with self._uow as uow:
            driver_id = await resolve_writable_driver_id(
                scope=scope,
                drivers=uow.drivers,
                user_id=user_id,
                requested_driver_id=command.driver_id,
            )

            vehicle = await uow.vehicles.get_by_id_or_none(command.vehicle_id)
            if vehicle is None:
                raise ValidationAppError("Veículo não encontrado nesta Empresa.")
            if not vehicle.accepts_new_usage:
                raise ValidationAppError(
                    f"O veículo {vehicle.plate} está '{vehicle.status.value}' e não pode receber "
                    "uma viagem nova."
                )

            driver = await uow.drivers.get_by_id_or_none(driver_id)
            if driver is None:
                raise ValidationAppError("Condutor não encontrado nesta Empresa.")
            if not driver.accepts_new_usage:
                raise ValidationAppError(
                    f"O condutor {driver.name} está inativo e não pode receber uma viagem nova."
                )

            usage = await uow.usages.create(
                NewVehicleUsage(
                    vehicle_id=command.vehicle_id,
                    driver_id=driver_id,
                    started_at=command.started_at,
                    ended_at=command.ended_at,
                    start_odometer=command.start_odometer,
                    end_odometer=command.end_odometer,
                    purpose=command.purpose,
                    notes=command.notes,
                    created_by=user_id,
                )
            )
            await uow.commit()
            return usage
