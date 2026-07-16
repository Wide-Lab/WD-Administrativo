from fastapi import APIRouter

from src.core.authz import set_permission_reader_factory
from src.core.security import set_user_reader_factory
from src.core.tenancy import set_organization_reader_factory
from src.modules.access.adapters.db.membership_reader import SqlAlchemyMembershipReader
from src.modules.access.adapters.db.organization_reader import SqlAlchemyOrganizationReader
from src.modules.access.adapters.http.routes import router as access_router
from src.modules.auth.adapters.db.user_reader import SqlAlchemyUserReader
from src.modules.auth.adapters.http.routes import router as auth_router


def mount_routes(api: APIRouter) -> None:
    """Registra os routers dos módulos no router `/api`. Adicionar um módulo é uma linha
    aqui — `app.include_router(<modulo>_router, prefix="/api")` — sem tocar em mais nada do
    `core`.

    `auth` e `access` são kernel e têm linha a mais: entregam ao `core` a implementação de uma
    porta — `UserReader`, `OrganizationReader`, `PermissionReader` —, e é isso que deixa
    `current_user`, `current_organization` e `require_permission` funcionarem sem o `core`
    importar um módulo. É privilégio de kernel: um app de negócio consome
    `CurrentUserDep`/`CurrentOrganizationDep`/`require_permission(...)` e pronto.

    O `access` chega a três linhas porque é dono dos três eixos que o kernel expõe além da
    identidade. É teto, não escada: a spec 05 registra o `require_module` do mesmo jeito, e um
    app de negócio segue com a sua linha única."""

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    set_user_reader_factory(SqlAlchemyUserReader)
    set_organization_reader_factory(SqlAlchemyOrganizationReader)
    set_permission_reader_factory(SqlAlchemyMembershipReader)

    api.include_router(auth_router)
    api.include_router(access_router)
