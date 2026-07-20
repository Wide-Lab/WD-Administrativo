import uuid

from src.core.exceptions import NotFoundError
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol


class DeleteUsageUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, usage_id: uuid.UUID) -> None:
        """Apaga um lançamento de viagem.

        **Exige `frota.usages.write` — o `write_own` fica de fora de propósito**, e a rota é a
        única do módulo em que as duas capabilities de escrita não se equivalem. O registro é a
        matéria-prima do relatório, e quem apaga a própria viagem apaga a evidência: corrigir,
        sim (`PATCH`); sumir, é ato do gestor. Quem só tem `write_own` nem chega aqui — o guard
        da rota nega antes.

        Diferente de veículo e condutor, aqui o `DELETE` apaga mesmo: um lançamento errado é
        ruído no relatório, não histórico. O que não se apaga é o carro e a pessoa.

        Raises:
            NotFoundError:
                Se a viagem não existir nesta Empresa.
        """

        async with self._uow as uow:
            if await uow.usages.get_by_id_or_none(usage_id) is None:
                raise NotFoundError("Viagem não encontrada.")

            await uow.usages.delete(usage_id)
            await uow.commit()
