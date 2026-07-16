"""users

Revision ID: 0001_users
Revises:
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import CITEXT, ENUM, UUID

revision: str = "0001_users"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # E-mail é CITEXT — a unicidade case-insensitive é do banco, não da aplicação.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    user_status = ENUM("active", "disabled", name="user_status", create_type=False)
    user_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", CITEXT(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        # Nulo enquanto o convidado não definiu senha (spec 06).
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column(
            "status",
            user_status,
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    ENUM(name="user_status").drop(op.get_bind(), checkfirst=True)
