"""Os models da frota.

Três tabelas, todas escopadas por `organization_id` com a **FK composta contra
`organizations(id, type)`** e o tipo fixado em coluna gerada — o mesmo truque de
`module_entitlements` (`05`), aqui garantindo que **só Empresa tem frota**.

`organizations` é tabela do `access`, e este arquivo **não importa `access`**: as FKs compostas
vivem só na migration, como `Membership.user_id` e `ModuleEntitlement.granted_by` já fazem.
Declará-las aqui exigiria que os models do `access` estivessem no mesmo `Base.metadata` no
momento em que o mapper resolve — módulo importando módulo, que é justamente o que sustenta o
seam de extração. Integridade referencial é do banco; o model só precisa da coluna.

Consequência a lembrar, herdada da `0004`: como os models não declaram essas FKs, um `alembic
revision --autogenerate` futuro vai propor dropá-las. Recuse."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from src.core.database.tenant import TenantScopedBase
from src.core.tenancy import OrganizationType
from src.modules.frota.domain.entities import DriverStatus, ReadingConfidence, VehicleStatus


def _pg_enum[EnumT: type[OrganizationType | VehicleStatus | DriverStatus | ReadingConfidence]](
    enum: EnumT,
    name: str,
) -> Enum:
    """Enum nativo do Postgres gravando os *valores* (`active`), não os nomes (`ACTIVE`).

    É uma cópia do helper de mesmo nome em `access/adapters/db/models.py`, e a duplicação é
    deliberada: importá-lo de lá seria módulo importando módulo. Ver `Como ficou` da spec 10."""

    return Enum(
        enum,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class CompanyScopedBase(TenantScopedBase):
    """Base das três tabelas da frota: escopo por Empresa, ancorado no banco.

    Herda de `TenantScopedBase` porque é isso que torna uma tabela elegível ao
    `TenantScopedRepository` do `core` — o escopo de tenant vira estrutural, e um use case que
    esqueça o `organization_id` continua correto.

    **E sobrescreve o `organization_id` pra tirar a FK simples que ele traz.** Não é para
    enfraquecer: é para trocá-la pela **composta** contra `organizations(id, type)`, que é
    estritamente mais forte — ela não só garante que a organização existe, garante que ela é uma
    `company`. As duas juntas seriam redundantes, e a simples ainda apareceria como diferença em
    todo `--autogenerate`.

    A composta vive **só na migration**: declará-la aqui exigiria que os models do `access`
    estivessem no mesmo `Base.metadata` quando o mapper resolve — módulo importando módulo, que é
    justamente o que sustenta o seam de extração. É a mesma decisão de `Membership.user_id`
    (spec 04) e de `ModuleEntitlement.granted_by` (spec 05), e herda a mesma dívida: um
    `--autogenerate` futuro vai propor dropar as três `fk_*_organization`. Recuse."""

    __abstract__ = True

    @declared_attr
    @classmethod
    def organization_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True))

    @declared_attr
    @classmethod
    def organization_type(cls) -> Mapped[OrganizationType]:
        """Constante gerada pelo banco — existe só pra ser o segundo lado da FK composta,
        fixando que `organization_id` referencia uma organização do tipo `company`. Ninguém
        escreve nela.

        É `declared_attr` e não um `Computed` compartilhado porque cada tabela precisa da sua
        própria instância: reusar o mesmo objeto entre models é o tipo de coisa que funciona até
        o dia em que o SQLAlchemy decide que não."""

        return mapped_column(
            _pg_enum(OrganizationType, "organization_type"),
            Computed(
                f"'{OrganizationType.COMPANY.value}'::organization_type",
                persisted=True,
            ),
        )


class Vehicle(CompanyScopedBase):
    """Um veículo da frota de uma Empresa.

    **Sem coluna de hodômetro atual**: ele é derivado do maior `end_odometer` registrado (ou do
    `initial_odometer`). Ver o docstring da entidade."""

    __tablename__ = "vehicles"

    __table_args__ = (
        # Duas Empresas podem ter a mesma placa (frota terceirizada, carro vendido de uma pra
        # outra); a mesma Empresa, não. É este único que faz o 409 de placa duplicada.
        UniqueConstraint("organization_id", "plate", name="uq_vehicles_organization_plate"),
        # Redundante como *chave* (o `id` já é PK), mas é o alvo da FK composta de
        # `vehicle_usages`. Mesmo papel do `uq_organizations_id_type` na spec 03.
        UniqueConstraint("id", "organization_id", name="uq_vehicles_id_organization"),
        Index("ix_vehicles_organization_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    plate: Mapped[str] = mapped_column(Text)
    """Normalizada em maiúsculas pela aplicação (`normalize_plate`) — sem isso o único acima
    deixaria `abc1d23` e `ABC1D23` conviverem."""

    brand: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    model_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    initial_odometer: Mapped[int] = mapped_column(Integer)
    """O hodômetro no dia do cadastro."""

    status: Mapped[VehicleStatus] = mapped_column(
        _pg_enum(VehicleStatus, "vehicle_status"),
        server_default=VehicleStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Driver(CompanyScopedBase):
    """Um condutor. Entidade própria, **não** um `membership` — ver o docstring da entidade."""

    __tablename__ = "drivers"

    __table_args__ = (
        # O alvo da FK composta de `vehicle_usages`.
        UniqueConstraint("id", "organization_id", name="uq_drivers_id_organization"),
        # Um usuário é no máximo um condutor na mesma Empresa, senão "lançar a própria viagem"
        # fica ambíguo — e `write_own` não teria como resolver de quem é o uso. Parcial porque
        # o condutor sem login é o caso comum, e `NULL` não colide com `NULL` de qualquer forma.
        Index(
            "uq_drivers_organization_user",
            "organization_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index("ix_drivers_organization_id", "organization_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    name: Mapped[str] = mapped_column(Text)

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    """O vínculo opcional com quem tem login.

    **Não tem FK, e é deliberado — este é o primeiro teste do seam de extração.** O precedente é
    `Membership.user_id`, que aponta pra `users` com a FK só na migration. Aqui vai um passo
    além: **não há FK nenhuma, nem na migration**. Uma FK de um app de negócio pra tabela do
    kernel é exatamente o que tornaria `frota` não-destacável — no dia em que ele tiver schema
    próprio, essa FK seria o que precisaria ser desfeito.

    O que sustenta a segurança disso é que um `user_id` obsoleto **não vaza nada**: pra alcançar
    qualquer rota de frota o chamador já precisa de vínculo ativo na Empresa
    (`current_organization`) e do entitlement (`require_module`). Um condutor apontando pra
    alguém que não é mais membro simplesmente nunca é alcançado. A frota **não valida** que o
    `user_id` é membro — validar exigiria ler `memberships`, que é do `access`, e a alternativa
    (uma porta nova no `core`) gastaria privilégio de kernel numa conveniência."""

    license_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    license_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Texto, não enum: as categorias mudam por resolução do Contran, e não vale uma migration
    por mudança de lei."""

    license_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    """Dado, sem alerta — notificar quem está pra vencer é compliance, e ganha spec própria."""

    status: Mapped[DriverStatus] = mapped_column(
        _pg_enum(DriverStatus, "driver_status"),
        server_default=DriverStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class OdometerReading(CompanyScopedBase):
    """Uma foto de painel e o que a máquina leu nela.

    **Esta tabela guarda o que a máquina disse; `vehicle_usages` guarda o que a pessoa
    confirmou** — os dois separados de propósito. A diferença entre eles é a taxa de erro do motor
    em produção, nos carros do cliente, e sobrescrever `value_read` com a correção humana apagaria
    exatamente esse dado."""

    __tablename__ = "odometer_readings"

    __table_args__ = (
        # O alvo da FK composta de `vehicle_usages` — mesmo papel do `uq_vehicles_id_organization`.
        UniqueConstraint("id", "organization_id", name="uq_odometer_readings_id_organization"),
        # Composta com `organization_id`, como as de `vehicle_usages`: é o que torna impossível
        # anexar a foto do carro da Empresa A a uma leitura da Empresa B. `vehicles` é tabela do
        # próprio `frota`, então esta FK **vive no model** — e por isso **não** entra na allowlist
        # do `alembic check`. Só a `fk_odometer_readings_organization`, que aponta pro `access`,
        # mora exclusivamente na migration.
        ForeignKeyConstraint(
            ["vehicle_id", "organization_id"],
            ["vehicles.id", "vehicles.organization_id"],
            name="fk_odometer_readings_vehicle",
        ),
        Index("ix_odometer_readings_organization_id", "organization_id"),
        # A purga oportunista varre por organização + idade, e o `count` do limite de 30/hora
        # varre por autor + idade. Sem este índice as duas viram seq scan a cada leitura.
        Index("ix_odometer_readings_created", "organization_id", "created_by", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    storage_key: Mapped[str] = mapped_column(Text)
    """Onde a foto está. **Montada pelo servidor**, e nunca vinda do cliente — aceitá-la de fora
    seria entregar leitura e escrita arbitrárias no bucket. Começa sempre pelo `organization_id`,
    o que faz apagar um tenant ou auditar consumo virar prefixo, não `SELECT`."""

    value_read: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """`NULL` = o motor se absteve. É resultado, não erro — e a linha (e a foto) são gravadas do
    mesmo jeito."""

    confidence: Mapped[ReadingConfidence] = mapped_column(
        _pg_enum(ReadingConfidence, "reading_confidence")
    )

    engine: Mapped[str] = mapped_column(Text)
    """`"openai:gpt-4o"`. Gravado porque **o motor vai trocar**, e sem esta coluna as duas
    populações ficariam misturadas na hora de medir a qualidade da leitura."""

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    """Id opaco, **sem FK**, mesma regra de `drivers.user_id`."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class VehicleUsage(CompanyScopedBase):
    """Uma viagem registrada.

    As FKs de veículo e condutor são **compostas com `organization_id`**, e não simples: é o que
    torna impossível registrar o carro da Empresa A com o motorista da Empresa B. Em multi-tenant
    com banco compartilhado, uma FK simples aceitaria a mistura, e o vazamento apareceria num
    relatório meses depois. As duas tabelas são do próprio `frota`, então **estas** FKs podem
    viver no model — diferente da FK contra `organizations`, que é do `access`."""

    __tablename__ = "vehicle_usages"

    __table_args__ = (
        # Compostas com `organization_id` — ver o docstring da classe. Estas duas apontam pra
        # tabelas do próprio `frota`, então podem viver aqui: nenhum import cruza fronteira.
        ForeignKeyConstraint(
            ["vehicle_id", "organization_id"],
            ["vehicles.id", "vehicles.organization_id"],
            name="fk_vehicle_usages_vehicle",
        ),
        ForeignKeyConstraint(
            ["driver_id", "organization_id"],
            ["drivers.id", "drivers.organization_id"],
            name="fk_vehicle_usages_driver",
        ),
        # As fotos, quando houve alguma. Compostas pelo mesmo motivo das duas de cima, e também
        # internas ao `frota` — então também podem viver no model.
        #
        # Como `organization_id` é NOT NULL e a coluna de leitura é nullable, o `MATCH SIMPLE`
        # default do Postgres deixa a linha passar quando a leitura é nula. É o que se quer: a
        # foto é **opcional**, e um módulo que a exigisse teria trocado uma folha de papel por
        # uma catraca.
        ForeignKeyConstraint(
            ["start_reading_id", "organization_id"],
            ["odometer_readings.id", "odometer_readings.organization_id"],
            name="fk_vehicle_usages_start_reading",
        ),
        ForeignKeyConstraint(
            ["end_reading_id", "organization_id"],
            ["odometer_readings.id", "odometer_readings.organization_id"],
            name="fk_vehicle_usages_end_reading",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="ck_vehicle_usages_period",
        ),
        CheckConstraint(
            "end_odometer IS NULL OR end_odometer >= start_odometer",
            name="ck_vehicle_usages_odometer",
        ),
        # Encerrar é atômico: uma viagem com hora de volta e sem hodômetro final é meia-linha
        # que estraga o relatório e ninguém repara. Ou fecha inteira, ou não fechou.
        CheckConstraint(
            "(ended_at IS NULL) = (end_odometer IS NULL)",
            name="ck_vehicle_usages_closed_together",
        ),
        # **A peça central desta spec.** Com registro em tempo real bastaria um índice único
        # parcial ("um veículo tem no máximo uma viagem aberta"); com lançamento retroativo,
        # alguém digita na sexta a viagem de terça e nada impediria que ela se sobrepusesse a
        # outra já registrada no mesmo carro — o veículo em dois lugares ao mesmo tempo, e o km
        # errado sem ninguém notar. A exclusão cobre os dois modos de uma vez, e entrega o índice
        # parcial de graça: `tstzrange(started_at, NULL)` é **sem limite superior**, então uma
        # viagem aberta colide com qualquer outra do mesmo veículo — inclusive outra aberta.
        #
        # Exige a extensão `btree_gist` (o `vehicle_id WITH =` sobre uuid), criada na migration.
        ExcludeConstraint(
            (text("vehicle_id"), "="),
            (text("tstzrange(started_at, ended_at)"), "&&"),
            name="ex_vehicle_usages_no_overlap",
            using="gist",
        ),
        Index("ix_vehicle_usages_organization_id", "organization_id"),
        Index("ix_vehicle_usages_vehicle_id", "vehicle_id"),
        Index("ix_vehicle_usages_driver_id", "driver_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    """Digitado, nunca `now()` do servidor. Data futura é recusada pela aplicação (422) — um
    `CHECK` com `now()` é impossível, porque `now()` não é imutável."""

    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    """`NULL` = viagem aberta."""

    start_odometer: Mapped[int] = mapped_column(Integer)
    """Digitado, e **sem default**. Em tempo real ele seria o final da viagem anterior; lançado
    fora de ordem, não é."""

    end_odometer: Mapped[int | None] = mapped_column(Integer, nullable=True)

    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    start_reading_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    end_reading_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    """As fotos de painel desta viagem. Nulas porque a foto é **opcional e continua sendo**.

    A referência mora aqui, e não um `usage_id` em `odometer_readings`, porque a pergunta que o
    produto faz é "qual a foto **desta** viagem" — e não "esta foto virou o quê". Órfã é leitura
    que ninguém aponta, e é ela que a purga recolhe."""

    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    """Quem lançou. Sem FK, mesma regra de `drivers.user_id` — id opaco de identidade."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
