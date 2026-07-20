"""frota

Revision ID: 0006_frota
Revises: 0005_invitations
Create Date: 2026-07-20

O primeiro app de negócio ganha schema. Três tabelas, todas escopadas por `organization_id` com
a FK composta contra `organizations(id, type)` e o tipo fixado em coluna gerada — o mesmo truque
de `module_entitlements` (0004), aqui garantindo que **só Empresa tem frota**.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision: str = "0006_frota"
down_revision: str | None = "0005_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Sem ela a constraint de exclusão de `vehicle_usages` não existe: `vehicle_id WITH =` é
    # igualdade de uuid num índice gist, que só o btree_gist ensina ao Postgres.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    organization_type = ENUM(name="organization_type", create_type=False)

    vehicle_status = ENUM(
        "active",
        "maintenance",
        "inactive",
        name="vehicle_status",
        create_type=False,
    )
    driver_status = ENUM("active", "inactive", name="driver_status", create_type=False)

    vehicle_status.create(op.get_bind(), checkfirst=True)
    driver_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "vehicles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        # Constante gerada pelo banco: existe só pra fixar, na FK composta abaixo, que só uma
        # Empresa tem frota. Ninguém escreve nela.
        sa.Column(
            "organization_type",
            organization_type,
            sa.Computed("'company'::organization_type", persisted=True),
            nullable=False,
        ),
        sa.Column("plate", sa.Text(), nullable=False),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("model_year", sa.Integer(), nullable=True),
        sa.Column("initial_odometer", sa.Integer(), nullable=False),
        sa.Column("status", vehicle_status, server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Duas Empresas podem ter a mesma placa (frota terceirizada, carro vendido de uma pra
        # outra); a mesma Empresa, não. É este único que faz o 409 de placa duplicada.
        sa.UniqueConstraint("organization_id", "plate", name="uq_vehicles_organization_plate"),
        # Redundante como chave, mas é o alvo da FK composta de `vehicle_usages`. Mesmo papel do
        # `uq_organizations_id_type` na 0002.
        sa.UniqueConstraint("id", "organization_id", name="uq_vehicles_id_organization"),
        # Só Empresa tem frota, e quem garante é o banco. Ela vive **só aqui**, e não no model:
        # `organizations` é tabela do `access`, e declará-la no model obrigaria os models da
        # frota a importar os do `access` — módulo importando módulo. Como o model não a declara,
        # um `--autogenerate` futuro vai propor dropá-la. Recuse.
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_vehicles_organization",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_vehicles_organization_id", "vehicles", ["organization_id"])

    op.create_table(
        "drivers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_type",
            organization_type,
            sa.Computed("'company'::organization_type", persisted=True),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        # **Sem FK, e nem aqui na migration** — diferente de `memberships.user_id` e de
        # `module_entitlements.granted_by`, que têm a FK no banco e só a escondem do model. Este
        # é o primeiro teste do seam de extração: uma FK de um app de negócio pra tabela do
        # kernel é exatamente o que tornaria `frota` não-destacável. A frota referencia
        # identidade por id opaco. Ver o docstring do model.
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("license_number", sa.Text(), nullable=True),
        # Texto e não enum: as categorias mudam por resolução do Contran, e não vale uma
        # migration por mudança de lei.
        sa.Column("license_category", sa.Text(), nullable=True),
        sa.Column("license_expires_at", sa.Date(), nullable=True),
        sa.Column("status", driver_status, server_default="active", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_drivers_id_organization"),
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_drivers_organization",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_drivers_organization_id", "drivers", ["organization_id"])
    # Um usuário é no máximo um condutor na mesma Empresa, senão "lançar a própria viagem" fica
    # ambíguo. Parcial porque o condutor sem login é o caso comum.
    op.create_index(
        "uq_drivers_organization_user",
        "drivers",
        ["organization_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "vehicle_usages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_type",
            organization_type,
            sa.Computed("'company'::organization_type", persisted=True),
            nullable=False,
        ),
        sa.Column("vehicle_id", UUID(as_uuid=True), nullable=False),
        sa.Column("driver_id", UUID(as_uuid=True), nullable=False),
        # Digitados, nunca `now()` do servidor: lançamento retroativo é o caso normal. O limite
        # de data futura é da aplicação (422) — um CHECK com `now()` é rejeitado pelo Postgres,
        # porque `now()` não é imutável.
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_odometer", sa.Integer(), nullable=False),
        sa.Column("end_odometer", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Quem lançou. Sem FK, mesma regra de `drivers.user_id`.
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Compostas com `organization_id`, e não simples: é o que torna impossível registrar o
        # carro da Empresa A com o motorista da Empresa B. Uma FK simples aceitaria a mistura, e
        # o vazamento apareceria num relatório meses depois.
        sa.ForeignKeyConstraint(
            ["vehicle_id", "organization_id"],
            ["vehicles.id", "vehicles.organization_id"],
            name="fk_vehicle_usages_vehicle",
        ),
        sa.ForeignKeyConstraint(
            ["driver_id", "organization_id"],
            ["drivers.id", "drivers.organization_id"],
            name="fk_vehicle_usages_driver",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_vehicle_usages_organization",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="ck_vehicle_usages_period",
        ),
        sa.CheckConstraint(
            "end_odometer IS NULL OR end_odometer >= start_odometer",
            name="ck_vehicle_usages_odometer",
        ),
        # Encerrar é atômico: uma viagem com hora de volta e sem hodômetro final é meia-linha que
        # estraga o relatório e ninguém repara. Ou fecha inteira, ou não fechou.
        sa.CheckConstraint(
            "(ended_at IS NULL) = (end_odometer IS NULL)",
            name="ck_vehicle_usages_closed_together",
        ),
    )
    op.create_index("ix_vehicle_usages_organization_id", "vehicle_usages", ["organization_id"])
    op.create_index("ix_vehicle_usages_vehicle_id", "vehicle_usages", ["vehicle_id"])
    op.create_index("ix_vehicle_usages_driver_id", "vehicle_usages", ["driver_id"])

    # A peça central da spec, e a razão do btree_gist acima. Com registro em tempo real bastaria
    # um índice único parcial ("um veículo tem no máximo uma viagem aberta"); com lançamento
    # retroativo, alguém digita na sexta a viagem de terça e nada impediria que ela se
    # sobrepusesse a outra já registrada no mesmo carro — o veículo em dois lugares ao mesmo
    # tempo. A exclusão cobre os dois modos de uma vez e entrega o índice parcial de graça:
    # `tstzrange(started_at, NULL)` é sem limite superior, então uma viagem aberta colide com
    # qualquer outra do mesmo veículo, inclusive outra aberta.
    #
    # Em SQL cru porque o `op.create_exclude_constraint` não alcança a expressão `tstzrange(...)`
    # — o model a declara com `ExcludeConstraint` e o DDL sai idêntico a este.
    op.execute(
        "ALTER TABLE vehicle_usages ADD CONSTRAINT ex_vehicle_usages_no_overlap "
        "EXCLUDE USING gist (vehicle_id WITH =, tstzrange(started_at, ended_at) WITH &&)"
    )


def downgrade() -> None:
    op.drop_table("vehicle_usages")

    op.drop_index("uq_drivers_organization_user", table_name="drivers")
    op.drop_index("ix_drivers_organization_id", table_name="drivers")
    op.drop_table("drivers")

    op.drop_index("ix_vehicles_organization_id", table_name="vehicles")
    op.drop_table("vehicles")

    ENUM(name="driver_status").drop(op.get_bind(), checkfirst=True)
    ENUM(name="vehicle_status").drop(op.get_bind(), checkfirst=True)

    # `btree_gist` fica: outra coisa pode ter passado a depender dela, e extensão não custa nada
    # parada. Dropá-la num downgrade seria efeito colateral fora do escopo desta revisão.
