from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, ClassVar, Final, Literal, Protocol


class DataclassInstance(Protocol):
    """Protocolo estrutural pra qualquer instância de dataclass."""

    __dataclass_fields__: ClassVar[dict[str, Any]]


class _Unset(Enum):
    UNSET = "UNSET"


UNSET: Final = _Unset.UNSET
"""Sentinela de "não informado" para comandos de atualização parcial."""

type UnsetType = Literal[_Unset.UNSET]


@dataclass(frozen=True, slots=True)
class BaseCreateCommand:
    """Base de comando de criação. Todos os campos são obrigatórios."""

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass(frozen=True, slots=True)
class BaseUpdateCommand:
    """Base de comando de atualização parcial. Campos não informados usam `UNSET` e são
    ignorados por `defined_values()`."""

    def defined_values(self) -> dict[str, Any]:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) is not UNSET
        }
