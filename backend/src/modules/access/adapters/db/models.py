import uuid
from datetime import datetime

from sqlalchemy import (
    Computed,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base_model import Base
from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import AgreementStatus, OrganizationStatus


def _pg_enum[EnumT: type[OrganizationType | OrganizationStatus | AgreementStatus]](
    enum: EnumT,
    name: str,
) -> Enum:
    """Enum nativo do Postgres gravando os *valores* (`company`), não os nomes (`COMPANY`)."""

    return Enum(
        enum,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


class Organization(Base):
    __tablename__ = "organizations"

    __table_args__ = (
        # O alvo das FKs compostas de `partner_agreements`. Redundante como *chave* (o `id` já
        # é PK), mas é ela que deixa um convênio referenciar "esta org, sendo deste tipo".
        UniqueConstraint("id", "type", name="uq_organizations_id_type"),
        # Exatamente uma `platform`: a Widelab como operadora. Índice único parcial —
        # `company` e `partner` seguem sem limite.
        Index(
            "uq_organizations_single_platform",
            "type",
            unique=True,
            postgresql_where=text("type = 'platform'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    type: Mapped[OrganizationType] = mapped_column(
        _pg_enum(OrganizationType, "organization_type"),
    )
    """Definido na criação e imutável — não há caminho na aplicação que o atualize, e o banco
    barra a troca enquanto um convênio referenciar a organização."""

    name: Mapped[str] = mapped_column(Text)

    document: Mapped[str | None] = mapped_column(Text, nullable=True)
    """CNPJ, quando houver."""

    status: Mapped[OrganizationStatus] = mapped_column(
        _pg_enum(OrganizationStatus, "organization_status"),
        server_default=OrganizationStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class PartnerAgreement(Base):
    __tablename__ = "partner_agreements"

    __table_args__ = (
        # Um convênio por par. Um Parceiro atende N Empresas, mas nunca a mesma duas vezes.
        UniqueConstraint("company_id", "partner_id", name="uq_partner_agreements_company_partner"),
        # Integridade de tipo, estrutural: uma FK simples pra `organizations(id)` aceitaria
        # qualquer organização dos dois lados. Apontando pra `organizations(id, type)` com o
        # tipo fixado em coluna gerada, inserir um `partner_id` que não é `partner` é
        # impossível, e mudar o `type` de uma org conveniada é bloqueado pelo banco. Não é
        # regra que vive só na aplicação.
        ForeignKeyConstraint(
            ["company_id", "company_type"],
            ["organizations.id", "organizations.type"],
            name="fk_partner_agreements_company",
        ),
        ForeignKeyConstraint(
            ["partner_id", "partner_type"],
            ["organizations.id", "organizations.type"],
            name="fk_partner_agreements_partner",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    partner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    company_type: Mapped[OrganizationType] = mapped_column(
        _pg_enum(OrganizationType, "organization_type"),
        Computed(f"'{OrganizationType.COMPANY.value}'::organization_type", persisted=True),
    )
    """Constante gerada pelo banco — existe só pra ser o segundo lado da FK composta, fixando
    que `company_id` referencia uma organização do tipo `company`. Ninguém escreve nela."""

    partner_type: Mapped[OrganizationType] = mapped_column(
        _pg_enum(OrganizationType, "organization_type"),
        Computed(f"'{OrganizationType.PARTNER.value}'::organization_type", persisted=True),
    )
    """O par da `company_type`, fixando o lado Parceiro do convênio."""

    status: Mapped[AgreementStatus] = mapped_column(
        _pg_enum(AgreementStatus, "agreement_status"),
        server_default=AgreementStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
