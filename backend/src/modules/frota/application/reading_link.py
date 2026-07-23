"""Amarrar uma foto a uma viagem — as três conferências, num lugar só.

Sem elas, uma foto viraria evidência de duas viagens diferentes, ou evidência do carro errado. E
a evidência que serve pra duas viagens não serve pra nenhuma.

Isto mora aqui, e não dentro de `CreateUsageUseCase`, porque **dois** use cases precisam da mesma
regra (`POST /usos` e `POST /usos/{id}/encerrar`) — mesma razão de `resolve_writable_driver_id`
existir separado."""

import uuid

from src.core.exceptions import ValidationAppError
from src.modules.frota.application.ports.repositories import (
    OdometerReadingRepositoryProtocol,
    VehicleUsageRepositoryProtocol,
)

__all__ = ["ensure_reading_usable"]


async def ensure_reading_usable(
    *,
    readings: OdometerReadingRepositoryProtocol,
    usages: VehicleUsageRepositoryProtocol,
    reading_id: uuid.UUID | None,
    vehicle_id: uuid.UUID,
) -> None:
    """Que esta leitura possa virar anexo **desta** viagem.

    Três conferências, e as três respondem **422** — não 404, porque quem manda o id não está
    navegando pra um recurso, está anexando um dado a um corpo que o servidor recusa por inteiro:

    1. **Mesma organização.** Sai de graça do repositório tenant-scoped: leitura de outra Empresa
       simplesmente não é encontrada.
    2. **Mesmo veículo.** A leitura é aninhada no veículo justamente porque é ele que dá o prior;
       anexar a foto do carro A à viagem do carro B faria a evidência mentir.
    3. **Ainda não apontada por outra viagem.**

    `reading_id=None` passa sem tocar o banco: a foto é **opcional e continua sendo**.

    Raises:
        ValidationAppError:
            Se a leitura não existir nesta Empresa, for de outro veículo, ou já estiver apontada.
    """

    if reading_id is None:
        return

    reading = await readings.get_by_id_or_none(reading_id)
    if reading is None:
        raise ValidationAppError("Leitura de hodômetro não encontrada nesta Empresa.")

    if reading.vehicle_id != vehicle_id:
        raise ValidationAppError(
            "Esta leitura de hodômetro é de outro veículo. A foto tem que ser do carro da viagem."
        )

    if await usages.is_reading_referenced(reading_id):
        raise ValidationAppError("Esta leitura de hodômetro já está anexada a outra viagem.")
