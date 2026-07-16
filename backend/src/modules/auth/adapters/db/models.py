import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Text, func
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database.base_model import Base
from src.modules.auth.domain.entities import UserStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )

    email: Mapped[str] = mapped_column(CITEXT, unique=True, index=True)
    """E-mail é sempre CITEXT — a unicidade é case-insensitive no banco, nunca por
    `String` + `.lower()` na aplicação."""

    name: Mapped[str] = mapped_column(Text)

    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Argon2id. Nulo enquanto o convidado não definiu senha (spec 06)."""

    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        server_default=UserStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
