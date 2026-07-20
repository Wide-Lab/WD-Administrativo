"""As dependencies da frota.

Note o que **não** está aqui: nenhum `set_*_factory`. Um app de negócio não registra porta no
`core` — isso é privilégio de kernel. A frota consome `CurrentUserDep`,
`CurrentOrganizationDep`, `require_permission(...)` e `require_module(...)` e pronto."""

from typing import Annotated

from fastapi import Depends, Query

from src.core.authz import Permission
from src.core.authz.context import PermissionReaderDep
from src.core.database.session import SessionDep
from src.core.exceptions import ForbiddenError
from src.core.pagination.params import PageParams
from src.core.security import CurrentUserDep
from src.core.tenancy import CurrentOrganization, CurrentOrganizationDep
from src.modules.frota.adapters.db.unit_of_work import FrotaUnitOfWork
from src.modules.frota.application.usage_scope import UsageScope


def get_unit_of_work(session: SessionDep, organization: CurrentOrganizationDep) -> FrotaUnitOfWork:
    """A unit of work já amarrada à organização do path.

    O `organization_id` vem de `current_organization`, que já validou o acesso de quem fez a
    requisição — nunca do corpo. É o que faz os repositórios tenant-scoped nascerem no tenant
    certo sem nenhum use case precisar lembrar disso."""

    return FrotaUnitOfWork(session=session, organization_id=organization.id)


def get_page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageParams:
    """Cópia do `get_page_params` do `access` — a mesma duplicação forçada da `PageResponse`, e
    pela mesma razão. Ver o docstring de `schemas.py`."""

    return PageParams(page=page, page_size=page_size)


async def granted_permissions(
    user: CurrentUserDep,
    organization: CurrentOrganizationDep,
    reader: PermissionReaderDep,
) -> frozenset[Permission]:
    """As capabilities de quem chama, **sem negar nada**.

    É a leitura que o `require_permission` faz por dentro antes de decidir — só que aqui o
    resultado é o dado, não a porta. O `GET /usos` precisa exatamente disso: a rota exige só o
    módulo, e é a capability que decide *o que ela devolve*.

    Vem de `src.core.authz.context` e não de `src.core.authz` porque a superfície pública do
    `core` exporta `require_permission` (que levanta) mas não o `PermissionReaderDep` (que só
    lê). Promovê-lo mudaria `src/core`, e o critério 1 da spec 10 proíbe. Ver `Como ficou`."""

    return await reader.get_permissions(user_id=user.id, organization_id=organization.id)


GrantedPermissionsDep = Annotated[frozenset[Permission], Depends(granted_permissions)]


async def get_usage_scope(granted: GrantedPermissionsDep) -> UsageScope:
    """As três capabilities de uso resolvidas pra quem chama."""

    return UsageScope.from_permissions(granted)


UsageScopeDep = Annotated[UsageScope, Depends(get_usage_scope)]


async def require_usage_write(
    organization: CurrentOrganizationDep,
    scope: UsageScopeDep,
) -> CurrentOrganization:
    """Guard de "pode lançar **alguma** coisa": `frota.usages.write` **ou** `write_own`.

    Existe porque `require_permission` decide sobre **uma** capability, e três rotas desta spec
    aceitam duas alternativas. De quem é o uso é pergunta seguinte, e quem a responde é
    `resolve_writable_driver_id` — este guard só derruba quem não tem nenhuma das duas, antes de
    o sistema ir ao banco descobrir se a pessoa é condutora."""

    if not scope.can_write_anything:
        raise ForbiddenError("Você não tem permissão para esta ação.")

    return organization
