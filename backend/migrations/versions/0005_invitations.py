"""invitations

Revision ID: 0005_invitations
Revises: 0004_module_entitlements
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, UUID

from src.modules.access.adapters.db.models import role_check_sql

revision: str = "0005_invitations"
down_revision: str | None = "0004_module_entitlements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    invitation_status = ENUM(
        "pending",
        "accepted",
        "revoked",
        "expired",
        name="invitation_status",
        create_type=False,
    )
    invitation_status.create(op.get_bind(), checkfirst=True)

    # Reusados: `membership_role` porque o papel prometido pelo convite é o papel que o vínculo
    # terá — um enum próprio poderia divergir do outro sem ninguém notar —, e
    # `organization_type` porque é o mesmo vocabulário de sempre.
    membership_role = ENUM(name="membership_role", create_type=False)
    organization_type = ENUM(name="organization_type", create_type=False)

    op.create_table(
        "invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        # CITEXT como em `users`: quem foi convidado como `Ana@x.com` aceita como `ana@x.com`.
        # Sem único — a mesma pessoa pode ser convidada por duas Empresas, e um convite
        # expirado não pode impedir um novo.
        sa.Column("email", CITEXT, nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        # Denormalizado de `organizations.type` e ancorado pela FK composta abaixo, como em
        # `memberships`: um CHECK não enxerga outra tabela.
        sa.Column("organization_type", organization_type, nullable=False),
        sa.Column("role", membership_role, nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("status", invitation_status, nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invited_by", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # A identidade é do `auth`; o convite é do `access`. Como em `memberships`, a FK cruza
        # os dois no schema compartilhado mas nenhum import cruza no Python — por isso ela
        # existe **só aqui**, e não no model.
        #
        # Consequência a lembrar: como o model não a declara, um `alembic revision
        # --autogenerate` futuro vai propor dropar `fk_invitations_invited_by`. Recuse.
        #
        # Sem `ondelete`: apagar quem convidou é bloqueado pelo banco, como em
        # `module_entitlements.granted_by`. Convidar é ato com responsável.
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name="fk_invitations_invited_by",
        ),
        # Fixa que `organization_type` é mesmo o tipo da organização apontada — sem isto o
        # CHECK abaixo seria decorativo.
        sa.ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_invitations_organization",
            ondelete="CASCADE",
        ),
        # A mesma regra de `memberships`, gerada da mesma função: não se convida um `hr` pra um
        # Parceiro. Vale já no convite pra o erro cair em quem convidou errado, e não na cara
        # do convidado no aceite.
        sa.CheckConstraint(
            role_check_sql(),
            name="ck_invitations_role_matches_organization_type",
        ),
    )
    op.create_index("ix_invitations_email", "invitations", ["email"])
    op.create_index("ix_invitations_organization_id", "invitations", ["organization_id"])
    # Único num índice só, como `ix_users_email` — o token é credencial de uso único, e um
    # `UniqueConstraint` além deste criaria um segundo índice idêntico pra manter de graça.
    op.create_index("ix_invitations_token", "invitations", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_invitations_token", table_name="invitations")
    op.drop_index("ix_invitations_organization_id", table_name="invitations")
    op.drop_index("ix_invitations_email", table_name="invitations")
    op.drop_table("invitations")
    ENUM(name="invitation_status").drop(op.get_bind(), checkfirst=True)
