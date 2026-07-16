from typing import Any

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class para os models SQLAlchemy da aplicação."""

    __mapper_args__: dict[str, Any] = {"eager_defaults": True}
    """Traz os valores gerados pelo banco (`server_default`, `onupdate`) já no RETURNING do
    INSERT/UPDATE.

    Sem isto, um `onupdate=func.now()` deixa a coluna expirada depois do UPDATE e a primeira
    leitura do atributo dispara um SELECT preguiçoso — que, num repositório async, estoura
    `MissingGreenlet`. É armadilha pra todo model com timestamp, então o padrão fica aqui."""
