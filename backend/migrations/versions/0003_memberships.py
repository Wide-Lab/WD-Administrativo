"""memberships

Revision ID: 0003_memberships
Revises: 0002_organizations
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

from src.modules.access.adapters.db.models import role_check_sql

revision: str = "0003_memberships"
down_revision: str | None = "0002_organizations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    membership_role = ENUM(
        "platform_admin",
        "company_admin",
        "hr",
        "finance",
        "manager",
        "collaborator",
        "partner_admin",
        "partner_operator",
        name="membership_role",
        create_type=False,
    )
    membership_role.create(op.get_bind(), checkfirst=True)

    membership_status = ENUM(
        "active",
        "disabled",
        name="membership_status",
        create_type=False,
    )
    membership_status.create(op.get_bind(), checkfirst=True)

    organization_type = ENUM(name="organization_type", create_type=False)

    op.create_table(
        "memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        # Denormalizado de `organizations.type` e ancorado pela FK composta abaixo. Existe
        # porque um CHECK não enxerga outra tabela, e o papel válido depende do tipo.
        sa.Column("organization_type", organization_type, nullable=False),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("status", membership_status, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Um papel por pessoa por organização nesta fase.
        sa.UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_organization"),
        # A identidade é do `auth`; o vínculo é do `access`. A FK cruza os dois no schema
        # compartilhado, mas nenhum import cruza no Python — e é por isso que ela existe
        # **só aqui**, e não no model: declará-la lá obrigaria `access` a importar os models
        # do `auth` pra resolver a tabela alvo. Ver o docstring de `Membership`.
        #
        # Consequência a lembrar: como o model não a declara, um `alembic revision
        # --autogenerate` futuro vai propor dropar `fk_memberships_user`. Recuse.
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memberships_user",
            ondelete="CASCADE",
        ),
        # Fixa que `organization_type` é mesmo o tipo da organização apontada — sem isto o
        # CHECK seria decorativo, bastaria gravar o tipo errado.
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_memberships_organization",
            ondelete="CASCADE",
        ),
        # Papel só é válido no tipo de organização correspondente: um `hr` não existe num
        # Parceiro. Gerado de `ROLES_BY_ORGANIZATION_TYPE` pra o banco não divergir do domínio.
        sa.CheckConstraint(
            role_check_sql(),
            name="ck_memberships_role_matches_organization_type",
        ),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_memberships_organization_id", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_table("memberships")
    ENUM(name="membership_status").drop(op.get_bind(), checkfirst=True)
    ENUM(name="membership_role").drop(op.get_bind(), checkfirst=True)
