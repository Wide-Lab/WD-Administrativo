"""module_entitlements

Revision ID: 0004_module_entitlements
Revises: 0003_memberships
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision: str = "0004_module_entitlements"
down_revision: str | None = "0003_memberships"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    organization_type = ENUM(name="organization_type", create_type=False)

    op.create_table(
        "module_entitlements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        # Constante gerada pelo banco: existe só pra fixar, na FK composta abaixo, que só uma
        # Empresa contrata módulo. Ninguém escreve nela.
        sa.Column(
            "organization_type",
            organization_type,
            sa.Computed("'company'::organization_type", persisted=True),
            nullable=False,
        ),
        # Uma chave do `ModuleRegistry` — que é código, não tabela. Sem FK de propósito: uma
        # tabela `modules` espelhando o registry seria uma segunda fonte da verdade, semeada por
        # migration a cada módulo novo. Ver o docstring do model.
        sa.Column("module_key", sa.Text(), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("granted_by", UUID(as_uuid=True), nullable=False),
        # Presença da linha = habilitado, ausência = negado. Este único é o que faz o `PUT` do
        # entitlement ser idempotente.
        sa.UniqueConstraint(
            "organization_id",
            "module_key",
            name="uq_module_entitlements_organization_module",
        ),
        # A identidade é do `auth`; o entitlement é do `access`. Como em `memberships`, a FK
        # cruza os dois no schema compartilhado mas nenhum import cruza no Python — por isso ela
        # existe **só aqui**, e não no model.
        #
        # Consequência a lembrar: como o model não a declara, um `alembic revision
        # --autogenerate` futuro vai propor dropar `fk_module_entitlements_granted_by`. Recuse.
        #
        # Sem `ondelete`: apagar quem liberou um módulo é bloqueado pelo banco. Cascatear
        # apagaria a venda junto com o funcionário que a registrou, e anular exigiria uma coluna
        # nullable pra dizer "alguém, não sei quem" — as duas perdem a responsabilidade que a
        # coluna existe pra guardar.
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
            name="fk_module_entitlements_granted_by",
        ),
        # Só Empresa contrata módulo, e quem garante é o banco: contra `organizations(id, type)`
        # com o tipo fixado na coluna gerada, ligar um módulo pra um Parceiro é impossível.
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_module_entitlements_organization",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_module_entitlements_organization_id",
        "module_entitlements",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_module_entitlements_organization_id", table_name="module_entitlements")
    op.drop_table("module_entitlements")
