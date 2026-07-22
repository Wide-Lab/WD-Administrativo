import uuid
from enum import StrEnum

from src.core.exceptions import NotFoundError
from src.core.storage import ObjectNotFoundError, ObjectStorage
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.application.usage_scope import UsageScope

__all__ = ["GetUsagePhotoUseCase", "PhotoSide"]


class PhotoSide(StrEnum):
    """Qual das duas fotos da viagem — em português, porque vira segmento de rota."""

    DEPARTURE = "saida"
    ARRIVAL = "chegada"


class GetUsagePhotoUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol, storage: ObjectStorage) -> None:
        self._uow = uow
        self._storage = storage

    async def execute(
        self,
        usage_id: uuid.UUID,
        side: PhotoSide,
        scope: UsageScope,
        user_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """Os bytes da foto, **servidos pela API**.

        Não é URL pré-assinada, e é decisão: presigned vaza uma URL que funciona por fora do
        `require_module` e do vínculo de tenant durante todo o TTL — mandada num grupo de
        WhatsApp, abre pra qualquer um. O volume aqui (uma foto por viagem, vista raramente) não
        paga esse risco.

        **O escopo é o mesmo de `GET /usos`**: quem tem `frota.usages.read` vê de toda a Empresa,
        quem não tem vê só as viagens do próprio condutor. E o que ele nega é **404**, nunca 403:
        um 403 confirmaria que a viagem de outro condutor existe, que é justamente o que o escopo
        esconde.

        Args:
            usage_id (uuid.UUID):
                A viagem.
            side (PhotoSide):
                Saída ou chegada.
            scope (UsageScope):
                As capabilities de uso de quem chama.
            user_id (uuid.UUID):
                Quem está pedindo — resolve o "próprio" de quem não tem `usages.read`.

        Returns:
            tuple[bytes, str]:
                Os bytes e o `content-type` gravado no storage.

        Raises:
            NotFoundError:
                Se a viagem não existir nesta Empresa, se ela estiver fora do escopo de quem
                pede, se ela não tiver aquela foto, ou se o objeto tiver sumido do storage.
        """

        async with self._uow as uow:
            usage = await uow.usages.get_by_id_or_none(usage_id)
            if usage is None:
                raise NotFoundError("Viagem não encontrada.")

            if not scope.can_read_any:
                own = await uow.drivers.get_by_user_id(user_id)
                if own is None or usage.driver_id != own.id:
                    raise NotFoundError("Viagem não encontrada.")

            reading_id = (
                usage.start_reading_id
                if side is PhotoSide.DEPARTURE
                else usage.end_reading_id
            )
            if reading_id is None:
                raise NotFoundError(f"Esta viagem não tem foto de {side.value}.")

            reading = await uow.readings.get_by_id_or_none(reading_id)
            if reading is None:  # pragma: no cover — a FK composta impede
                raise NotFoundError("Leitura de hodômetro não encontrada.")

        try:
            return await self._storage.get(reading.storage_key)
        except ObjectNotFoundError as exc:
            # A linha existe e o arquivo não: é inconsistência de infra, não um pedido inválido.
            # Ainda assim 404 — quem pediu a foto não tem o que fazer com um 500, e a exceção
            # original fica no `__cause__` pro log.
            raise NotFoundError("A foto desta viagem não está mais disponível.") from exc
