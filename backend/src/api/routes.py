from fastapi import APIRouter

from src.api.modules import FROTA, REFEICOES
from src.core.authz import set_permission_reader_factory
from src.core.modules import mount_module, set_module_entitlement_reader_factory
from src.core.security import set_user_directory_factory, set_user_reader_factory
from src.core.tenancy import set_organization_reader_factory
from src.modules.access.adapters.db.entitlement_reader import SqlAlchemyModuleEntitlementReader
from src.modules.access.adapters.db.membership_reader import SqlAlchemyMembershipReader
from src.modules.access.adapters.db.organization_reader import SqlAlchemyOrganizationReader
from src.modules.access.adapters.http.routes import router as access_router
from src.modules.access.domain.permissions import validate_module_grants
from src.modules.auth.adapters.db.user_directory import SqlAlchemyUserDirectory
from src.modules.auth.adapters.db.user_reader import SqlAlchemyUserReader
from src.modules.auth.adapters.http.routes import router as auth_router


def mount_routes(api: APIRouter) -> None:
    """Registra os módulos no router `/api`.

    Um app de negócio é **uma linha**: `mount_module(api, <descritor>)`. Ela registra o módulo
    no catálogo e pendura as rotas dele sob `/organizacoes/{orgId}/<chave>`, atrás do
    `require_module` — sem tocar em mais nada do `core`.

    `auth` e `access` são kernel e têm linha a mais: entregam ao `core` a implementação de uma
    porta — `UserReader`, `UserDirectory`, `OrganizationReader`, `PermissionReader`,
    `ModuleEntitlementReader` —, e é isso que deixa `current_user`, `current_organization`,
    `require_permission` e `require_module` funcionarem, e o onboarding criar identidade, sem o
    `core` importar um módulo. É privilégio de kernel: um app de negócio consome
    `CurrentUserDep`/`CurrentOrganizationDep`/`require_permission(...)` e pronto.

    O `access` fica nas **quatro** linhas que a spec 05 chamou de teto, e o teto se sustentou:
    a spec 06 não somou eixo nenhum aqui. Quem cresceu foi o `auth`, de uma linha pra
    **duas** — `UserReader` lê identidade, `UserDirectory` cria. A spec 02 tinha registrado o
    `UserReader` como "o único caso em que um módulo tem duas linhas"; a 06 mostrou que faltava
    o outro lado do verbo, porque o onboarding é do `access` e a tabela `users` é do `auth`.
    Um app de negócio segue com a sua linha única (`refeicoes` e `frota`, abaixo, já são só
    isso)."""

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    set_user_reader_factory(SqlAlchemyUserReader)
    set_user_directory_factory(SqlAlchemyUserDirectory)
    set_organization_reader_factory(SqlAlchemyOrganizationReader)
    set_permission_reader_factory(SqlAlchemyMembershipReader)
    set_module_entitlement_reader_factory(SqlAlchemyModuleEntitlementReader)

    api.include_router(auth_router)
    api.include_router(access_router)

    mount_module(api, REFEICOES)
    mount_module(api, FROTA)

    # Depois de **todos** os `mount_module`, e uma vez só: confere que nenhum módulo concede a um
    # papel que não existe nem à Plataforma (spec 09). Não é uma quinta porta do `access` — é
    # verificação, não registro de um `Reader`, e o teto de quatro linhas segue de pé. O `core` já
    # cobrou o namespace em `register_module`; o papel só o `access` enxerga, porque `Role` é dele.
    validate_module_grants()
