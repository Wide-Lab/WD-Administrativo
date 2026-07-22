"""Fotografar o painel e devolver o número — guardando a foto como evidência."""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.core.exceptions import NotFoundError, TooManyRequestsError, ValidationAppError
from src.core.storage import ObjectStorage
from src.modules.frota.application.dtos.commands import ReadOdometerCommand
from src.modules.frota.application.photo_validation import ensure_valid_photo
from src.modules.frota.application.ports.odometer_reader import OdometerReader
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import NewOdometerReading, OdometerReading
from src.modules.frota.domain.rules import is_plausible, odometer_delta, storage_key_for

logger = logging.getLogger(__name__)

MAX_READINGS_PER_USER_PER_HOUR = 30
"""Um dedo travado no botão custa dinheiro de fornecedor. Trinta por hora é folgado pra quem
lança viagem de verdade — e o 429 nada grava, nem linha nem objeto."""

ORPHAN_AGE_HOURS = 24
ORPHAN_PURGE_LIMIT = 50


@dataclass(frozen=True, slots=True)
class OdometerReadingOutcome:
    """O que a rota devolve: a leitura gravada e a frase conferível que o prior permite montar."""

    reading: OdometerReading
    last_odometer: int
    plausible: bool
    delta: int | None


class ReadOdometerUseCase:
    def __init__(
        self,
        uow: FrotaUnitOfWorkProtocol,
        storage: ObjectStorage,
        reader: OdometerReader,
    ) -> None:
        self._uow = uow
        self._storage = storage
        self._reader = reader

    async def execute(
        self,
        command: ReadOdometerCommand,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        now: datetime | None = None,
    ) -> OdometerReadingOutcome:
        """Valida a foto, lê o hodômetro e grava linha **e** objeto.

        A ordem não é acidental. Primeiro o que é barato e não toca o banco (tamanho, formato,
        decodificação), depois o veículo — que é quem dá o prior, e sem prior a resposta seria um
        número solto —, depois o teto de leituras, e só então o motor, que é a parte que custa
        dinheiro e segundos.

        **O motor se abster não é erro.** `value=None` responde 201 com a foto guardada do mesmo
        jeito: a leitura aconteceu, o resultado é "não sei", e a evidência vale igual. O que se
        quer evitar é o palpite confiante — foi ele que condenou o caminho sem IA.

        Args:
            command (ReadOdometerCommand):
                O veículo e os bytes da foto.
            user_id (uuid.UUID):
                Quem fotografou — vira `created_by` e é o eixo do teto de 30/hora.
            organization_id (uuid.UUID):
                A Empresa do path. Prefixo da chave de storage.
            now (datetime | None):
                O agora, injetável pra o teste não depender do relógio.

        Returns:
            OdometerReadingOutcome:
                A leitura gravada, o prior, e o `plausivel`/`delta` derivados dos dois.

        Raises:
            PayloadTooLargeError | UnsupportedMediaTypeError | ValidationAppError:
                Se a foto não passar em `ensure_valid_photo`.
            NotFoundError:
                Se o veículo não existir nesta Empresa.
            ValidationAppError:
                Se o veículo estiver `inactive` ou `maintenance`.
            TooManyRequestsError:
                Se esta pessoa passar de 30 leituras na última hora.
        """

        now = now or datetime.now(UTC)

        ensure_valid_photo(command.content, command.content_type)

        async with self._uow as uow:
            vehicle = await uow.vehicles.get_by_id_or_none(command.vehicle_id)
            if vehicle is None:
                # 404 e não 403: a resposta não pode virar oráculo de que o veículo existe em
                # alguma outra Empresa. Mesma decisão do `GET /veiculos/{id}` da spec 10.
                raise NotFoundError("Veículo não encontrado.")

            if not vehicle.accepts_new_usage:
                raise ValidationAppError(
                    f"O veículo {vehicle.plate} está '{vehicle.status.value}' e não pode receber "
                    "uma viagem nova, então não há o que fotografar."
                )

            recentes = await uow.readings.count_by_user_since(
                user_id=user_id,
                since=now - timedelta(hours=1),
            )
            if recentes >= MAX_READINGS_PER_USER_PER_HOUR:
                raise TooManyRequestsError(
                    "Muitas leituras seguidas. Espere um minuto e tente de novo."
                )

            purgadas = await self._delete_orphan_rows(uow, now)

            result = await self._reader.read(command.content, command.content_type)
            if result.value is None:
                logger.info(
                    "Leitura de hodômetro sem valor (veículo %s, motor %s): %s",
                    vehicle.id,
                    result.engine,
                    result.note,
                )

            reading_id = uuid.uuid7()
            key = storage_key_for(organization_id, reading_id, command.content_type)

            # A linha primeiro, o objeto depois, o commit por último. Se o `put` falhar, a
            # transação inteira volta e não sobra nem linha nem objeto; se a ordem fosse
            # invertida, um erro de banco deixaria um objeto que ninguém aponta e que a purga —
            # que varre linhas — nunca encontraria.
            reading = await uow.readings.create(
                NewOdometerReading(
                    id=reading_id,
                    vehicle_id=vehicle.id,
                    storage_key=key,
                    value_read=result.value,
                    confidence=result.confidence,
                    engine=result.engine,
                    created_by=user_id,
                )
            )

            await self._storage.put(key, command.content, command.content_type)
            await uow.commit()

        # Os objetos das órfãs só somem **depois** do commit que apagou as linhas delas. Se a
        # transação tivesse voltado atrás, as linhas voltariam — e apagar os arquivos antes teria
        # deixado leituras válidas apontando pro nada, que é pior que o lixo que a purga recolhe.
        await self._delete_orphan_objects(purgadas)

        return OdometerReadingOutcome(
            reading=reading,
            last_odometer=vehicle.current_odometer,
            plausible=(
                is_plausible(result.value, vehicle.current_odometer)
                if result.value is not None
                else False
            ),
            delta=odometer_delta(result.value, vehicle.current_odometer),
        )

    async def _delete_orphan_rows(
        self,
        uow: FrotaUnitOfWorkProtocol,
        now: datetime,
    ) -> list[str]:
        """Apaga as **linhas** de até 50 leituras da Empresa com mais de 24h e sem viagem
        apontando, e devolve as chaves cujos objetos precisam sumir junto.

        Leitura que nunca virou viagem é a pessoa que fotografou e fechou o diálogo: lixo com foto
        junto. A purga é **oportunista**, na própria rota de leitura, e não agendada, porque o
        projeto não tem scheduler — inventar um pra isso seria trocar um problema de 50 linhas por
        um de infra. Fica registrado como o que é: solução modesta, que vira job no dia em que
        houver onde pendurá-lo.

        As linhas saem **nesta transação**, junto com a leitura nova: ou as duas coisas
        aconteceram, ou nenhuma."""

        orfas = await uow.readings.list_orphans(
            older_than=now - timedelta(hours=ORPHAN_AGE_HOURS),
            limit=ORPHAN_PURGE_LIMIT,
        )
        if not orfas:
            return []

        await uow.readings.delete_many([orfa.id for orfa in orfas])
        return [orfa.storage_key for orfa in orfas]

    async def _delete_orphan_objects(self, keys: list[str]) -> None:
        """Os arquivos das órfãs, depois do commit.

        Falhar aqui **não** derruba a leitura de quem está esperando: a linha já sumiu, o objeto
        vira lixo invisível, e limpeza é higiene — a pessoa de pé ao lado do carro não tem nada
        com isso. O erro vai pro log, que é onde ele pode ser cobrado."""

        for key in keys:
            try:
                await self._storage.delete(key)
            except Exception:
                logger.exception("Não consegui apagar a foto órfã %s; a leitura segue.", key)
