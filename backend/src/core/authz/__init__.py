"""Superfície de autorização do `core`.

É daqui que qualquer módulo — de kernel ou de negócio — exige uma permissão na organização
ativa, sem nunca importar `access`."""

from src.core.authz.context import (
    Permission,
    PermissionReader,
    require_permission,
    set_permission_reader_factory,
)

__all__ = [
    "Permission",
    "PermissionReader",
    "require_permission",
    "set_permission_reader_factory",
]
