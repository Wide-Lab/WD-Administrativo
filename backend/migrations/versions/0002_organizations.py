"""organizations e partner_agreements

Revision ID: 0002_organizations
Revises: 0001_users
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision: str = "0002_organizations"
down_revision: str | None = "0001_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLATFORM_ORGANIZATION_ID = "01890000-0000-7000-8000-000000000001"
"""A Widelab como operadora. Id fixo porque é um singleton do sistema: o bootstrap do
primeiro `platform_admin` (spec 02/04) precisa de um alvo estável pra apontar."""


def upgrade() -> None:
    organization_type = ENUM(
        "platform",
        "company",
        "partner",
        name="organization_type",
        create_type=False,
    )
    organization_type.create(op.get_bind(), checkfirst=True)

    organization_status = ENUM(
        "active",
        "disabled",
        name="organization_status",
        create_type=False,
    )
    organization_status.create(op.get_bind(), checkfirst=True)

    agreement_status = ENUM(
        "active",
        "suspended",
        name="agreement_status",
        create_type=False,
    )
    agreement_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("type", organization_type, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        # CNPJ, quando houver.
        sa.Column("document", sa.Text(), nullable=True),
        sa.Column("status", organization_status, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Alvo das FKs compostas de `partner_agreements`: redundante como chave (o `id` já é
        # PK), mas é o que permite referenciar "esta org, sendo deste tipo".
        sa.UniqueConstraint("id", "type", name="uq_organizations_id_type"),
    )

    # Exatamente uma `platform`. `company` e `partner` seguem sem limite.
    op.create_index(
        "uq_organizations_single_platform",
        "organizations",
        ["type"],
        unique=True,
        postgresql_where=sa.text("type = 'platform'"),
    )

    op.create_table(
        "partner_agreements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", UUID(as_uuid=True), nullable=False),
        # Constantes geradas pelo banco: existem só pra fixar o tipo de cada lado do convênio
        # na FK composta abaixo. Ninguém escreve nelas.
        sa.Column(
            "company_type",
            organization_type,
            sa.Computed("'company'::organization_type", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "partner_type",
            organization_type,
            sa.Computed("'partner'::organization_type", persisted=True),
            nullable=False,
        ),
        sa.Column("status", agreement_status, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Um convênio por par: um Parceiro atende N Empresas, nunca a mesma duas vezes.
        sa.UniqueConstraint(
            "company_id",
            "partner_id",
            name="uq_partner_agreements_company_partner",
        ),
        # Integridade de tipo estrutural: uma FK simples pra `organizations(id)` aceitaria
        # qualquer org dos dois lados. Contra `organizations(id, type)`, inserir um
        # `partner_id` que não é `partner` é impossível, e mudar o `type` de uma org
        # conveniada é bloqueado pelo banco.
        sa.ForeignKeyConstraint(
            ["company_id", "company_type"],
            ["organizations.id", "organizations.type"],
            name="fk_partner_agreements_company",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id", "partner_type"],
            ["organizations.id", "organizations.type"],
            name="fk_partner_agreements_partner",
        ),
    )
    op.create_index(
        "ix_partner_agreements_company_id",
        "partner_agreements",
        ["company_id"],
    )
    op.create_index(
        "ix_partner_agreements_partner_id",
        "partner_agreements",
        ["partner_id"],
    )

    # A organização plataforma é um dado de estrutura, não de negócio: o sistema não é
    # coerente sem ela, e nenhuma rota a cria (`POST /api/organizacoes` só faz Empresa e
    # Parceiro). Semear aqui é o que torna "existe exatamente uma platform" verdade desde o
    # primeiro `upgrade head`.
    op.execute(
        sa.text(
            "INSERT INTO organizations (id, type, name, status) "
            "VALUES (CAST(:id AS uuid), 'platform', 'Widelab', 'active')"
        ).bindparams(id=PLATFORM_ORGANIZATION_ID)
    )


def downgrade() -> None:
    op.drop_index("ix_partner_agreements_partner_id", table_name="partner_agreements")
    op.drop_index("ix_partner_agreements_company_id", table_name="partner_agreements")
    op.drop_table("partner_agreements")
    op.drop_index("uq_organizations_single_platform", table_name="organizations")
    op.drop_table("organizations")
    ENUM(name="agreement_status").drop(op.get_bind(), checkfirst=True)
    ENUM(name="organization_status").drop(op.get_bind(), checkfirst=True)
    ENUM(name="organization_type").drop(op.get_bind(), checkfirst=True)
