"""As regras puras da frota: normalização de placa, data futura e o agrupamento do relatório.

Tudo aqui é função de dados pra dados — sem sessão, sem I/O, sem FastAPI. É o que a spec manda
testar em `tests/unit/frota/`, que roda **sem Docker**."""

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

__all__ = [
    "ALLOWED_PHOTO_TYPES",
    "MAX_PHOTO_BYTES",
    "MAX_PHOTO_PIXELS",
    "MileageGroup",
    "MileageGroupBy",
    "MileageSummary",
    "PLAUSIBLE_MAX_DELTA_KM",
    "UsageForReport",
    "is_future",
    "is_plausible",
    "normalize_plate",
    "odometer_delta",
    "storage_key_for",
    "summarize_mileage",
]

MAX_PHOTO_BYTES = 8 * 1024 * 1024
"""8 MB. Acima disso é 413, e o frontend reduz pra 1600px antes de subir justamente pra nunca
chegar aqui."""

MAX_PHOTO_PIXELS = 50_000_000
"""50 MP **depois de decodificada** — anti-bomba de descompressão. 8 MB de PNG viram gigabytes na
memória se o servidor decodificar sem olhar, e o teto de bytes sozinho não pega isso."""

ALLOWED_PHOTO_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
"""**HEIC não entra** (415). O iPhone fotografa em HEIC, mas o frontend reencoda pra JPEG antes de
subir, então o formato nunca chega aqui — e aceitá-lo custaria `pillow-heif` no container por um
caminho que ninguém percorre."""

PLAUSIBLE_MAX_DELTA_KM = 2000
"""O teto de uma viagem única. Acima disso é quase certo erro de leitura ou de digitação.

**É sinal, nunca bloqueio.** Um carro que rodou 2.100 km numa viagem existe, e recusá-lo faria a
pessoa inventar um número — a spec 10 já decidiu que divergência de hodômetro é aviso, e a foto
não muda essa decisão."""

_PHOTO_SUFFIXES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def normalize_plate(plate: str) -> str:
    """A placa como ela vai pro banco: sem espaço nas pontas e em maiúsculas.

    A normalização é da aplicação (a spec diz "normalizada em maiúsculas pela aplicação"), e é o
    que faz o `UNIQUE (organization_id, plate)` significar o que promete: sem ela, `abc1d23` e
    `ABC1D23` seriam duas linhas e o mesmo carro apareceria duas vezes no relatório.

    **Não** mexe em hífen nem em espaço interno de propósito: `ABC-1D23` e `ABC1D23` seguem
    distintos. Unificá-los é palpite sobre formato de placa (Mercosul mudou o padrão uma vez e
    pode mudar de novo), e o custo do palpite errado é recusar uma placa legítima como duplicada.
    Se doer, é decisão de produto — não um `replace` escondido aqui."""

    return plate.strip().upper()


def is_future(moment: datetime, now: datetime) -> bool:
    """Se `moment` está à frente de `now`.

    **É a única regra desta spec que o banco não consegue impor**: um `CHECK (started_at <=
    now())` é rejeitado pelo Postgres, porque `now()` não é imutável e não entra em `CHECK`.
    Então ela vive aqui, e o use case a traduz em 422.

    Retroativo é o caso normal da frota — o que se recusa é o **futuro**. Sem esse limite,
    "retroativo" vira "qualquer data" e some a última âncora de sanidade.

    **Os dois lados precisam ter fuso.** Comparar um ingênuo com um aware é `TypeError` em Python,
    e quem garante que `moment` tem fuso é a borda HTTP (`AwareDatetime` nos schemas), não um
    `if` aqui: normalizar um instante sem fuso exigiria escolher um, e essa escolha é do cliente
    que sabe onde a viagem foi digitada."""

    return moment > now


def is_plausible(value: int, last_odometer: int) -> bool:
    """Se o número lido cabe entre o último hodômetro conhecido e ele mais 2.000 km.

    ```
    plausivel = ultimo_hodometro <= valor <= ultimo_hodometro + 2000
    ```

    Abaixo do último, o hodômetro andou pra trás; muito acima, alguém leu um dígito a mais. As
    duas bordas são **inclusivas**: `valor == ultimo` é o carro que não rodou desde o último
    registro (plausível), e `ultimo + 2000` é o teto, não o primeiro valor recusado.

    **O resultado nunca vira 4xx** — ele é um sinal pra tela, que mostra um aviso e deixa lançar
    assim mesmo. Ver `PLAUSIBLE_MAX_DELTA_KM`."""

    return last_odometer <= value <= last_odometer + PLAUSIBLE_MAX_DELTA_KM


def odometer_delta(value: int | None, last_odometer: int) -> int | None:
    """Quantos quilômetros o carro rodou desde o último registro, ou `None` se não houve leitura.

    É o que transforma a resposta de um número solto numa frase conferível — *"li 45.210, o último
    registrado foi 45.180, +30 km"* — e é o que faz a pessoa confirmar num segundo em vez de
    reconferir dígito a dígito. Pode ser negativo: hodômetro que anda pra trás é justamente o que
    o aviso existe pra mostrar."""

    if value is None:
        return None
    return value - last_odometer


def storage_key_for(organization_id: uuid.UUID, reading_id: uuid.UUID, content_type: str) -> str:
    """A chave da foto no storage: `{organization_id}/frota/hodometro/{id}.{ext}`.

    **Sempre começa pelo tenant**, e não é segurança (a autorização é das rotas) — é operação:
    apagar um tenant, auditar consumo ou mover uma Empresa de bucket vira prefixo, não `SELECT`.

    **A chave nunca vem do cliente**, que só conhece o `id` da leitura. Aceitá-la de fora seria
    entregar leitura e escrita arbitrárias no bucket."""

    suffix = _PHOTO_SUFFIXES.get(content_type, ".bin")
    return f"{organization_id}/frota/hodometro/{reading_id}{suffix}"


class MileageGroupBy(StrEnum):
    """O eixo do relatório de quilometragem."""

    VEHICLE = "veiculo"
    DRIVER = "condutor"


@dataclass(frozen=True, slots=True)
class UsageForReport:
    """O mínimo que o relatório precisa de um uso. Um recorte, e não a entidade inteira, pra o
    agrupamento ser testável sem montar `VehicleUsage` completo."""

    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    start_odometer: int
    end_odometer: int | None


@dataclass(frozen=True, slots=True)
class MileageGroup:
    """Uma linha do relatório: um veículo (ou um condutor) e o que ele rodou no período."""

    id: uuid.UUID
    label: str
    total_km: int
    closed_usages: int
    open_usages: int
    """As viagens sem hora de volta. Contadas à parte e **nunca somadas como zero km** — "não
    sei" e "não rodou" não podem virar o mesmo número, senão o relatório mente pra baixo sem
    ninguém notar."""


@dataclass(frozen=True, slots=True)
class MileageSummary:
    group_by: MileageGroupBy
    groups: list[MileageGroup]


def summarize_mileage(
    usages: Iterable[UsageForReport],
    group_by: MileageGroupBy,
    labels: Mapping[uuid.UUID, str],
) -> MileageSummary:
    """Soma `end_odometer - start_odometer` dos usos **encerrados**, agrupado por veículo ou por
    condutor.

    O uso aberto entra em `open_usages` e não contribui com quilômetro nenhum — ver
    `MileageGroup.open_usages`.

    A divergência de hodômetro entre viagens (painel trocado, carro que rodou sem registro) não é
    tratada aqui e **não** vira erro: ela aparece no relatório como lacuna, que é o desenho da
    spec — travar o lançamento faria o usuário inventar um número, que é pior que o buraco.

    Args:
        usages (Iterable[UsageForReport]):
            Os usos do período, já filtrados pelo repositório.
        group_by (MileageGroupBy):
            O eixo do agrupamento.
        labels (Mapping[uuid.UUID, str]):
            O nome de cada veículo/condutor, pra a linha não sair só com um id.

    Returns:
        MileageSummary:
            Os grupos, ordenados por `label`.
    """

    totals: dict[uuid.UUID, list[int]] = {}

    for usage in usages:
        key = usage.vehicle_id if group_by is MileageGroupBy.VEHICLE else usage.driver_id
        bucket = totals.setdefault(key, [0, 0, 0])

        if usage.end_odometer is None:
            bucket[2] += 1
            continue

        bucket[0] += usage.end_odometer - usage.start_odometer
        bucket[1] += 1

    groups = [
        MileageGroup(
            id=key,
            label=labels.get(key, ""),
            total_km=total_km,
            closed_usages=closed,
            open_usages=open_,
        )
        for key, (total_km, closed, open_) in totals.items()
    ]
    groups.sort(key=lambda group: (group.label, str(group.id)))

    return MileageSummary(group_by=group_by, groups=groups)
