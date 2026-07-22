"""As entidades da frota: veículo, condutor e registro de uso.

Nada aqui importa `auth` nem `access` — um app de negócio depende só de `src.core` e dos
contracts do kernel. As referências a identidade (`Driver.user_id`, `VehicleUsage.created_by`)
são **id opaco, sem FK**, e é isso que mantém o seam de extração limpo. Ver o docstring de
`Driver.user_id` no model."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from src.core.types import UNSET, BaseCreateCommand, BaseUpdateCommand, UnsetType

__all__ = [
    "Driver",
    "DriverStatus",
    "NewDriver",
    "NewOdometerReading",
    "NewVehicle",
    "NewVehicleUsage",
    "OdometerReading",
    "ReadingConfidence",
    "UpdateDriver",
    "UpdateOdometerReading",
    "UpdateVehicle",
    "UpdateVehicleUsage",
    "Vehicle",
    "VehicleStatus",
    "VehicleUsage",
]


class VehicleStatus(StrEnum):
    """O estado de um veículo na frota.

    Não há `DELETE` de veículo: um carro vendido vira `INACTIVE` e continua nos relatórios do
    período em que rodou. Apagar levaria junto o histórico, que é o produto."""

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"


class DriverStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ReadingConfidence(StrEnum):
    """O quanto o motor confia no número que leu.

    Três degraus e não um float porque a tela decide **uma** coisa com isto (mostrar aviso ou
    não), e um `0.72` obrigaria a inventar o corte em algum lugar — provavelmente em dois lugares
    diferentes. `LOW` acompanha toda abstenção."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class Vehicle:
    """Um veículo da frota de uma Empresa.

    **Não tem coluna de hodômetro atual**, e isso é decisão: `current_odometer` é derivado, sai
    por `LEFT JOIN` sobre um agregado e nunca é gravado. Guardá-lo seria uma segunda fonte da
    verdade, pronta pra divergir da primeira no primeiro lançamento retroativo fora de ordem."""

    id: uuid.UUID
    organization_id: uuid.UUID
    plate: str
    brand: str
    model: str
    model_year: int | None
    initial_odometer: int
    status: VehicleStatus
    created_at: datetime
    current_odometer: int
    """O maior hodômetro que o sistema conhece deste carro: o `initial_odometer`, o maior
    `end_odometer` registrado ou o `start_odometer` de uma viagem **aberta** — o que for maior.

    A viagem aberta entra porque um carro na rua já rodou: ignorá-la faria o prior de um veículo
    em viagem apontar pra antes da saída.

    **Derivado, nunca coluna** — ver o docstring da classe. Quem o calcula é o repositório, numa
    query só (sem N+1)."""

    @property
    def accepts_new_usage(self) -> bool:
        """Só veículo `active` recebe uso novo. Um `CHECK` não enxerga outra tabela, então quem
        impõe isto é a aplicação — ver `Regras que a aplicação impõe` na spec."""

        return self.status is VehicleStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class NewVehicle(BaseCreateCommand):
    """Note a ausência de `organization_id`: quem o carimba é o `TenantScopedRepository`, a
    partir da organização ativa. Não há caminho pra gravar na organização de outro."""

    plate: str
    brand: str
    model: str
    initial_odometer: int
    model_year: int | None = None
    status: VehicleStatus = VehicleStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateVehicle(BaseUpdateCommand):
    plate: str | UnsetType = UNSET
    brand: str | UnsetType = UNSET
    model: str | UnsetType = UNSET
    model_year: int | None | UnsetType = UNSET
    initial_odometer: int | UnsetType = UNSET
    status: VehicleStatus | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class Driver:
    """Um condutor — **entidade própria, não um `membership`**.

    Decisão de produto: o motorista terceirizado, o prestador e o entregador dirigem e nunca vão
    logar. Exigir login de todo condutor forçaria cadastrar usuário-fantasma pra gente que não
    usa o sistema, e o resultado seria dado sujo. Quem **também** é usuário ganha o `user_id` e
    passa a poder lançar a própria viagem (`frota.usages.write_own`)."""

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    user_id: uuid.UUID | None
    license_number: str | None
    license_category: str | None
    license_expires_at: date | None
    status: DriverStatus
    created_at: datetime

    @property
    def accepts_new_usage(self) -> bool:
        return self.status is DriverStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class NewDriver(BaseCreateCommand):
    name: str
    user_id: uuid.UUID | None = None
    license_number: str | None = None
    license_category: str | None = None
    license_expires_at: date | None = None
    status: DriverStatus = DriverStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateDriver(BaseUpdateCommand):
    name: str | UnsetType = UNSET
    user_id: uuid.UUID | None | UnsetType = UNSET
    license_number: str | None | UnsetType = UNSET
    license_category: str | None | UnsetType = UNSET
    license_expires_at: date | None | UnsetType = UNSET
    status: DriverStatus | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class VehicleUsage:
    """Uma viagem: quem pegou qual carro, quando saiu, quando voltou e com quantos quilômetros.

    `started_at` e `ended_at` são **digitados**, nunca `now()` do servidor: a premissa honesta é
    que ninguém abre o app na portaria, e a viagem é lançada depois — às vezes dias depois, às
    vezes por outra pessoa. Não existe rota "iniciar viagem agora"."""

    id: uuid.UUID
    organization_id: uuid.UUID
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    start_odometer: int
    end_odometer: int | None
    purpose: str | None
    notes: str | None
    created_by: uuid.UUID
    created_at: datetime
    start_reading_id: uuid.UUID | None = None
    end_reading_id: uuid.UUID | None = None
    """As fotos de painel desta viagem, quando houve alguma.

    **Nulas porque a foto é opcional e continua sendo**: quem quiser digitar, digita. Um módulo
    que exigisse foto pra lançar viagem teria trocado uma folha de papel por uma catraca.

    A referência mora **na viagem**, e não um `usage_id` na leitura, porque a pergunta que o
    produto faz é "qual a foto **desta** viagem" — e não "esta foto virou o quê". Órfã é leitura
    que ninguém aponta, e é ela que a purga recolhe."""

    @property
    def is_open(self) -> bool:
        """Viagem sem hora de volta. `ck_vehicle_usages_closed_together` garante que
        `ended_at` e `end_odometer` são nulos juntos — não há meia-linha."""

        return self.ended_at is None

    @property
    def distance(self) -> int | None:
        """Os quilômetros rodados, ou `None` se a viagem ainda está aberta.

        `None` e não `0`: "não sei" e "não rodou" não podem virar o mesmo número — é a regra que
        faz o relatório contar viagem aberta à parte em vez de somá-la como zero."""

        if self.end_odometer is None:
            return None
        return self.end_odometer - self.start_odometer


@dataclass(frozen=True, slots=True)
class NewVehicleUsage(BaseCreateCommand):
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    started_at: datetime
    start_odometer: int
    created_by: uuid.UUID
    ended_at: datetime | None = None
    end_odometer: int | None = None
    purpose: str | None = None
    notes: str | None = None
    start_reading_id: uuid.UUID | None = None
    end_reading_id: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateVehicleUsage(BaseUpdateCommand):
    """Sem `created_by`: quem lançou é registro, não campo editável.

    `vehicle_id` e `driver_id` entram porque corrigir o carro ou o condutor de um lançamento
    errado é caso real — e as FKs compostas garantem que a correção não cruza tenant.

    **Sem `start_reading_id`/`end_reading_id` também, e é decisão**: corrigir a foto de uma
    viagem já lançada é caso raro o bastante pra esperar quem peça, e a ausência aqui é o que
    faz o `PATCH` não aceitá-los sem precisar de um `if` na rota."""

    vehicle_id: uuid.UUID | UnsetType = UNSET
    driver_id: uuid.UUID | UnsetType = UNSET
    started_at: datetime | UnsetType = UNSET
    ended_at: datetime | None | UnsetType = UNSET
    start_odometer: int | UnsetType = UNSET
    end_odometer: int | None | UnsetType = UNSET
    purpose: str | None | UnsetType = UNSET
    notes: str | None | UnsetType = UNSET


@dataclass(frozen=True, slots=True)
class OdometerReading:
    """Uma foto de painel e o que a máquina leu nela.

    **Esta tabela guarda o que a máquina disse; `vehicle_usages` guarda o que a pessoa
    confirmou.** Os dois separados de propósito: a diferença entre eles é a taxa de erro do motor
    em produção, nos carros do cliente — a medição que o spike não pôde fazer. Sobrescrever
    `value_read` com a correção humana apagaria exatamente esse dado.

    A foto fica guardada mesmo quando o motor se absteve: a leitura aconteceu, o resultado é "não
    sei", e a evidência vale igual."""

    id: uuid.UUID
    organization_id: uuid.UUID
    vehicle_id: uuid.UUID
    storage_key: str
    """Onde a foto está. **Montada pelo servidor**, sempre — o cliente só conhece o `id`."""

    value_read: int | None
    """O que o motor leu, ou `None` se ele se absteve. Abster-se é **resposta**, não falha: o que
    se quer evitar é o palpite confiante que o Tesseract deu em 83% das vezes no spike."""

    confidence: ReadingConfidence
    engine: str
    """`"openai:gpt-4o"` — gravado em cada linha porque **o motor vai trocar**, de modelo, de
    fornecedor, ou pra um local no dia em que compensar. Sem esta coluna, medir a qualidade da
    leitura depois de uma troca misturaria as duas populações."""

    created_by: uuid.UUID
    """Id opaco, **sem FK**, como `drivers.user_id`."""

    created_at: datetime


@dataclass(frozen=True, slots=True)
class NewOdometerReading(BaseCreateCommand):
    """O `id` entra explícito, e é o único comando de criação do projeto que faz isso: a chave de
    storage é derivada dele, e a foto precisa estar gravada sob a chave certa antes de a linha
    existir. Deixar o banco sortear o `id` obrigaria a gravar a linha, ler o `id` e só então
    montar a chave — um `UPDATE` a mais pra nada."""

    id: uuid.UUID
    vehicle_id: uuid.UUID
    storage_key: str
    value_read: int | None
    confidence: ReadingConfidence
    engine: str
    created_by: uuid.UUID


@dataclass(frozen=True, slots=True)
class UpdateOdometerReading(BaseUpdateCommand):
    """**Vazio de propósito: leitura não se corrige.**

    O que a máquina disse é registro, e sobrescrevê-lo com a correção humana apagaria a única
    medida de erro do motor em produção — que é justamente o que separar esta tabela de
    `vehicle_usages` existe pra preservar. A correção da pessoa vira `start_odometer`/
    `end_odometer` na viagem, do outro lado.

    Existe só porque o `TenantScopedRepository` do `core` é genérico sobre um comando de
    atualização, e sem nenhum campo ele não tem como ser instanciado com efeito."""
