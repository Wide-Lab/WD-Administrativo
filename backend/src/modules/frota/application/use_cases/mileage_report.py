from datetime import datetime

from src.core.exceptions import ValidationAppError
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.rules import MileageGroupBy, MileageSummary, summarize_mileage


class MileageReportUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(
        self,
        started_from: datetime,
        started_until: datetime,
        group_by: MileageGroupBy = MileageGroupBy.VEHICLE,
    ) -> MileageSummary:
        """O relatório que justifica o modelo inteiro — a pergunta que a folha de papel na
        portaria existe pra responder.

        Soma `end_odometer - start_odometer` dos usos **encerrados** no período, agrupado por
        veículo ou por condutor. Os usos abertos entram como contagem à parte e **nunca como
        zero km**: "não sei" e "não rodou" não podem virar o mesmo número.

        A divergência de hodômetro entre viagens (painel trocado, carro que rodou sem registro)
        aparece como lacuna e não vira erro — travar o lançamento faria o usuário inventar um
        número, que é pior que o buraco.

        Args:
            started_from (datetime):
                Início do período, obrigatório.
            started_until (datetime):
                Fim do período, obrigatório.
            group_by (MileageGroupBy):
                O eixo do agrupamento; veículo por default.

        Returns:
            MileageSummary:
                Os grupos, ordenados por rótulo.

        Raises:
            ValidationAppError:
                Se o período estiver invertido.
        """

        if started_until < started_from:
            raise ValidationAppError("A data final do período não pode ser anterior à inicial.")

        async with self._uow as uow:
            usages = await uow.usages.list_for_report(
                started_from=started_from,
                started_until=started_until,
            )
            labels = (
                await uow.vehicles.labels()
                if group_by is MileageGroupBy.VEHICLE
                else await uow.drivers.labels()
            )

        return summarize_mileage(usages=usages, group_by=group_by, labels=labels)
