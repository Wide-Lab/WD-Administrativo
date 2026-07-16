"""O guard de entitlement: cada Empresa só enxerga os módulos que contratou.

A decisão comercial da `00-visao-geral.md` vive aqui, e é imposta **no backend**: não basta o
frontend esconder o menu. Negação por padrão — a ausência de linha em `module_entitlements` é
o "não"."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import SessionDep
from src.core.exceptions import ForbiddenError
from src.core.modules.registry import ModuleKey
from src.core.tenancy import (
    CurrentOrganization,
    CurrentOrganizationDep,
    OrganizationId,
    OrganizationType,
)


class ModuleEntitlementReader(Protocol):
    """Porta de leitura de entitlement. Existe pro `core` resolver `require_module` sem
    importar `access` — quem a implementa é o `access`, dono de `module_entitlements`. Mesmo
    padrão do `UserReader` (spec 02), do `OrganizationReader` (spec 03) e do
    `PermissionReader` (spec 04)."""

    async def is_enabled(
        self,
        organization_id: OrganizationId,
        module_key: ModuleKey,
    ) -> bool:
        """Se a organização tem o módulo habilitado. Presença da linha = habilitado; ausência
        = negado."""
        ...


type ModuleEntitlementReaderFactory = Callable[[AsyncSession], ModuleEntitlementReader]

_module_entitlement_reader_factory: ModuleEntitlementReaderFactory | None = None


def set_module_entitlement_reader_factory(factory: ModuleEntitlementReaderFactory) -> None:
    """Liga a implementação de `ModuleEntitlementReader` ao `core`. Chamada uma vez em
    `mount_routes` pelo kernel `access`."""

    global _module_entitlement_reader_factory
    _module_entitlement_reader_factory = factory


async def get_module_entitlement_reader(session: SessionDep) -> ModuleEntitlementReader:
    if _module_entitlement_reader_factory is None:
        raise RuntimeError(
            "Nenhum ModuleEntitlementReader registrado. O kernel `access` deve chamar "
            "set_module_entitlement_reader_factory() em mount_routes."
        )
    return _module_entitlement_reader_factory(session)


ModuleEntitlementReaderDep = Annotated[
    ModuleEntitlementReader,
    Depends(get_module_entitlement_reader),
]


def require_module(
    key: ModuleKey,
) -> Callable[[CurrentOrganization, ModuleEntitlementReader], Awaitable[CurrentOrganization]]:
    """Guard de entitlement: 403 se a organização do path não tiver o módulo habilitado.

    `mount_module` já o pendura em todas as rotas do módulo, então um app de negócio raramente
    precisa nomeá-lo; compõe com `require_permission` quando a rota quer as duas negações
    explícitas:

        @router.post("/tickets", dependencies=[Depends(require_module("refeicoes")),
                                               Depends(require_permission("catalog.write"))])

    **Não pergunta quem é o usuário — pergunta o que o tenant contratou.** As duas perguntas
    são diferentes, e é por isso que este guard não mora no `authz`: `require_permission`
    afrouxa pra `platform_admin`, e aqui não há afrouxamento nenhum. Um módulo que a Empresa
    não comprou não abre nem pra Widelab: entitlement é fato comercial, não privilégio.

    Só Empresa contrata módulo — `platform` e `partner` não têm entitlement e levam 403. Como
    o Parceiro alcança um módulo da Empresa que ele atende (pelo convênio) é decisão do
    primeiro app de negócio a precisar disso, na fase 2."""

    async def dependency(
        organization: CurrentOrganizationDep,
        reader: ModuleEntitlementReaderDep,
    ) -> CurrentOrganization:
        if organization.type is not OrganizationType.COMPANY:
            raise ForbiddenError("Este módulo pertence a uma Empresa.")

        if not await reader.is_enabled(organization_id=organization.id, module_key=key):
            raise ForbiddenError("Esta organização não tem este módulo habilitado.")

        return organization

    return dependency
