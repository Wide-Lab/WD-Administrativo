"""Superfície de tenancy do `core`.

É daqui que qualquer módulo — de kernel ou de negócio — consome a organização ativa da
requisição, sem nunca importar `access`."""

from src.core.tenancy.context import (
    CurrentOrganization,
    CurrentOrganizationDep,
    OrganizationId,
    OrganizationReader,
    OrganizationType,
    current_organization,
    set_organization_reader_factory,
)

__all__ = [
    "CurrentOrganization",
    "CurrentOrganizationDep",
    "OrganizationId",
    "OrganizationReader",
    "OrganizationType",
    "current_organization",
    "set_organization_reader_factory",
]
