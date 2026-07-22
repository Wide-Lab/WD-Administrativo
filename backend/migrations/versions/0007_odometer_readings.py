"""odometer_readings

Revision ID: 0007_odometer_readings
Revises: 0006_frota
Create Date: 2026-07-22

A foto do painel vira evidência. Uma tabela nova, escopada por `organization_id` com a FK composta
contra `organizations(id, type)` e o tipo fixado em coluna gerada — o mesmo truque das três da
0006 —, e duas colunas novas em `vehicle_usages` apontando pra ela.

**A allowlist do `alembic check` vai de seis para sete.** As duas FKs de `vehicle_usages` pra
`odometer_readings` são internas ao `frota` e vivem no model, então não contam; a
`fk_odometer_readings_organization` **cruza módulo** — como as três equivalentes da 0006 — e por
isso vive só aqui, fora do model. Um `--autogenerate` futuro vai propor dropá-la. Recuse.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision: str = "0007_odometer_readings"
down_revision: str | None = "0006_frota"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    organization_type = ENUM(name="organization_type", create_type=False)

    reading_confidence = ENUM(
        "high",
        "medium",
        "low",
        name="reading_confidence",
        create_type=False,
    )
    reading_confidence.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "odometer_readings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "organization_type",
            organization_type,
            sa.Computed("'company'::organization_type", persisted=True),
            nullable=False,
        ),
        sa.Column("vehicle_id", UUID(as_uuid=True), nullable=False),
        # Montada pelo servidor, sempre — o cliente só conhece o `id` da leitura. Começa pelo
        # `organization_id`: apagar um tenant ou auditar consumo vira prefixo, não SELECT.
        sa.Column("storage_key", sa.Text(), nullable=False),
        # NULL = o motor se absteve. É resultado, não erro: a linha e a foto ficam do mesmo jeito.
        sa.Column("value_read", sa.Integer(), nullable=True),
        sa.Column("confidence", reading_confidence, nullable=False),
        # `openai:gpt-4o`. Gravado porque o motor vai trocar — sem esta coluna, medir a qualidade
        # da leitura em produção depois de uma troca misturaria as duas populações.
        sa.Column("engine", sa.Text(), nullable=False),
        # Sem FK, mesma regra de `drivers.user_id`: id opaco de identidade.
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # O alvo da FK composta de `vehicle_usages`.
        sa.UniqueConstraint(
            "id",
            "organization_id",
            name="uq_odometer_readings_id_organization",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id", "organization_id"],
            ["vehicles.id", "vehicles.organization_id"],
            name="fk_odometer_readings_vehicle",
        ),
        # Só Empresa tem frota, e quem garante é o banco. Vive **só aqui**, e não no model:
        # `organizations` é tabela do `access`. Um `--autogenerate` futuro vai propor dropá-la —
        # é a sétima da allowlist. Recuse.
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_odometer_readings_organization",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_odometer_readings_organization_id",
        "odometer_readings",
        ["organization_id"],
    )
    # A purga oportunista varre por organização + idade; o limite de 30 leituras por hora conta
    # por autor + idade. Sem este índice as duas viram seq scan a cada leitura.
    op.create_index(
        "ix_odometer_readings_created",
        "odometer_readings",
        ["organization_id", "created_by", "created_at"],
    )

    # Nulas porque a foto é **opcional e continua sendo**: quem quiser digitar, digita. Um módulo
    # que exigisse foto pra lançar viagem teria trocado uma folha de papel por uma catraca.
    op.add_column(
        "vehicle_usages",
        sa.Column("start_reading_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "vehicle_usages",
        sa.Column("end_reading_id", UUID(as_uuid=True), nullable=True),
    )

    # Compostas com `organization_id`, como as de veículo e condutor. Internas ao `frota`, então
    # estas duas **também vivem no model** — não entram na allowlist do `alembic check`.
    #
    # O `MATCH SIMPLE` default deixa a linha passar quando a coluna de leitura é nula, que é
    # exatamente o que a foto opcional precisa.
    op.create_foreign_key(
        "fk_vehicle_usages_start_reading",
        "vehicle_usages",
        "odometer_readings",
        ["start_reading_id", "organization_id"],
        ["id", "organization_id"],
    )
    op.create_foreign_key(
        "fk_vehicle_usages_end_reading",
        "vehicle_usages",
        "odometer_readings",
        ["end_reading_id", "organization_id"],
        ["id", "organization_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_vehicle_usages_end_reading", "vehicle_usages", type_="foreignkey")
    op.drop_constraint("fk_vehicle_usages_start_reading", "vehicle_usages", type_="foreignkey")
    op.drop_column("vehicle_usages", "end_reading_id")
    op.drop_column("vehicle_usages", "start_reading_id")

    op.drop_index("ix_odometer_readings_created", table_name="odometer_readings")
    op.drop_index("ix_odometer_readings_organization_id", table_name="odometer_readings")
    op.drop_table("odometer_readings")

    ENUM(name="reading_confidence").drop(op.get_bind(), checkfirst=True)
