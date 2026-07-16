import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base_model import Base


class TenantScopedBase(Base):
    """Base de toda tabela **de negócio**: escopo por linha, banco e schema compartilhados.

    Herdar daqui é o que torna uma tabela elegível ao `TenantScopedRepository` — e é por isso
    que o escopo é estrutural, não disciplina: um model de negócio que esqueça o
    `organization_id` simplesmente não tem repositório tenant-scoped pra usar.

    O `organization_id` viaja junto se um módulo for extraído um dia (o *seam* da
    `00-visao-geral.md`).

    A FK aponta pra `organizations`, tabela do `access`, por **nome** — o `core` não importa o
    módulo, e a seta continua apontando pra dentro."""

    __abstract__ = True

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        index=True,
    )
