"""Superfície de módulos do `core`.

É daqui que um app de negócio se declara (`ModuleDescriptor`), pluga (`mount_module`) e exige
o próprio entitlement (`require_module`) — sem nunca importar `access`, dono da tabela.

Registro e entitlement são coisas diferentes e ambas moram aqui: o registry diz o que a
plataforma **sabe oferecer**; o entitlement diz o que **este tenant contratou**."""

from src.core.modules.entitlements import (
    ModuleEntitlementReader,
    require_module,
    set_module_entitlement_reader_factory,
)
from src.core.modules.mount import mount_module
from src.core.modules.registry import (
    ModuleDescriptor,
    ModuleKey,
    ModuleNav,
    ModulePersona,
    get_module,
    is_registered,
    register_module,
    registered_modules,
)

__all__ = [
    "ModuleDescriptor",
    "ModuleEntitlementReader",
    "ModuleKey",
    "ModuleNav",
    "ModulePersona",
    "get_module",
    "is_registered",
    "mount_module",
    "register_module",
    "registered_modules",
    "require_module",
    "set_module_entitlement_reader_factory",
]
