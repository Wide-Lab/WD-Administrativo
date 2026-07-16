import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
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
from src.modules.access.domain.entities import (
    AgreementStatus,
    MembershipStatus,
    OrganizationStatus,
    Role,
)
from src.modules.access.domain.permissions import ROLES_BY_ORGANIZATION_TYPE


def _pg_enum[
    EnumT: type[OrganizationType | OrganizationStatus | AgreementStatus | Role | MembershipStatus]
](
    enum: EnumT,
    name: str,
) -> Enum:
    """Enum nativo do Postgres gravando os *valores* (`company`), não os nomes (`COMPANY`)."""

    return Enum(
        enum,
        name=name,
        values_callable=lambda members: [member.value for member in members],
    )


def role_check_sql() -> str:
    """O `CHECK` de papel×tipo de organização, gerado a partir de `ROLES_BY_ORGANIZATION_TYPE`.

    Gerado, e não escrito à mão, pra o banco e o mapa do domínio não poderem divergir — se um
    papel novo entrar no mapa sem migration, o `--autogenerate` acusa. A migration `0003`
    importa esta mesma função."""

    clauses = [
        "(organization_type = '{type}' AND role IN ({roles}))".format(
            type=organization_type.value,
            roles=", ".join(f"'{role.value}'" for role in sorted(roles)),
        )
        for organization_type, roles in ROLES_BY_ORGANIZATION_TYPE.items()
    ]
    return " OR ".join(clauses)


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


class Membership(Base):
    """O vínculo usuário↔organização↔papel.

    **`user_id` não declara `ForeignKey` aqui, e isso é deliberado.** A FK pra `users` existe
    — está na migration `0003` e o banco a impõe —, mas declará-la no model exigiria que a
    tabela `users` estivesse no mesmo `Base.metadata` no momento em que o mapper resolve, ou
    seja, que **este arquivo importasse os models do `auth`**. Isso é módulo importando
    módulo, que é justamente o que sustenta o seam de extração. O custo apareceu rodando: a
    CLI do `access`, que não tem motivo pra conhecer `auth`, quebrava com
    `NoReferencedTableError`.

    Integridade referencial é do banco; o model só precisa da coluna. `organization_id` segue
    com FK porque `organizations` é tabela do próprio `access`."""

    __tablename__ = "memberships"

    __table_args__ = (
        # Um papel por pessoa por organização nesta fase.
        UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_organization"),
        # Integridade de tipo, como no convênio (spec 03): a FK composta fixa que
        # `organization_type` é *mesmo* o tipo da organização apontada — não um palpite da
        # aplicação —, e o CHECK abaixo se apoia nela pra decidir se o papel existe naquele
        # tipo. Sem a FK composta o CHECK seria decorativo: bastaria gravar o tipo errado.
        ForeignKeyConstraint(
            ["organization_id", "organization_type"],
            ["organizations.id", "organizations.type"],
            name="fk_memberships_organization",
            ondelete="CASCADE",
        ),
        # Um `hr` não existe num Parceiro. Isto é o critério 2 da spec 04, e ele vive no
        # banco: um `INSERT` por fora da aplicação falha igual.
        CheckConstraint(role_check_sql(), name="ck_memberships_role_matches_organization_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    """Aponta pra `users.id`, tabela do `auth`. A FK vive na migration — ver o docstring da
    classe."""

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)

    organization_type: Mapped[OrganizationType] = mapped_column(
        _pg_enum(OrganizationType, "organization_type"),
    )
    """Denormalizado de `organizations.type`, e não escolha de quem escreve: a FK composta o
    ancora na organização real. Existe só pra dar ao `CHECK` acesso ao tipo — um `CHECK` não
    enxerga outra tabela."""

    role: Mapped[Role] = mapped_column(_pg_enum(Role, "membership_role"))

    status: Mapped[MembershipStatus] = mapped_column(
        _pg_enum(MembershipStatus, "membership_status"),
        server_default=MembershipStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
