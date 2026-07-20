import uuid

from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.modules.frota.application.dtos.commands import CloseUsageCommand
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.application.usage_scope import UsageScope
from src.modules.frota.domain.entities import VehicleUsage


class CloseUsageUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        usage_id: uuid.UUID,
        command: CloseUsageCommand,
        scope: UsageScope,
        user_id: uuid.UUID,
    ) -> VehicleUsage:
        """Encerra uma viagem: grava `ended_at` e `end_odometer` **juntos**.

        É o gesto mais frequente do módulo inteiro — a única coisa que o Colaborador faz — e tem
        rota própria, não um `PATCH`: encerrar uma viagem já encerrada é **409**, enquanto
        corrigir uma encerrada é `PATCH` e é legítimo. Espremer as duas num `PATCH` faria "fechar"
        e "corrigir" indistinguíveis no log e na permissão.

        O 409 sai de um `UPDATE ... WHERE ended_at IS NULL`, e não de um `if` sobre um estado
        lido antes: dois encerramentos simultâneos passariam os dois pela checagem, e o segundo
        sobrescreveria o primeiro em silêncio.

        Raises:
            NotFoundError:
                Se a viagem não existir nesta Empresa.
            ForbiddenError:
                Se quem só tem `write_own` encerrar a viagem de outro condutor.
            ConflictError:
                Se a viagem já estiver encerrada.
        """

        async with self._uow as uow:
            usage = await uow.usages.get_by_id_or_none(usage_id)
            if usage is None:
                raise NotFoundError("Viagem não encontrada.")

            if not scope.can_write_any:
                own = await uow.drivers.get_by_user_id(user_id)
                if own is None or usage.driver_id != own.id:
                    raise ForbiddenError("Você só pode encerrar as suas próprias viagens.")

            closed = await uow.usages.close_if_open(
                usage_id,
                ended_at=command.ended_at,
                end_odometer=command.end_odometer,
            )
            if not closed:
                raise ConflictError(
                    "Esta viagem já foi encerrada. Para corrigir os dados dela, use a edição."
                )

            await uow.commit()

            updated = await uow.usages.get_by_id_or_none(usage_id)
            if updated is None:
                raise NotFoundError("Viagem não encontrada.")
            return updated
