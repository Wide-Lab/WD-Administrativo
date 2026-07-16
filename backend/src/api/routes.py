from fastapi import FastAPI

from src.core.security import set_user_reader_factory
from src.core.tenancy import set_organization_reader_factory
from src.modules.access.adapters.db.organization_reader import SqlAlchemyOrganizationReader
from src.modules.access.adapters.http.routes import router as access_router
from src.modules.auth.adapters.db.user_reader import SqlAlchemyUserReader
from src.modules.auth.adapters.http.routes import router as auth_router


def mount_routes(app: FastAPI) -> None:
    """Registra os routers dos módulos no router `/api`. Adicionar um módulo é uma linha
    aqui — `app.include_router(<modulo>_router, prefix="/api")` — sem tocar em mais nada do
    `core`.

    `auth` e `access` são kernel e têm uma linha a mais cada: entregam ao `core` a
    implementação de uma porta — `UserReader` e `OrganizationReader` —, e é isso que deixa
    `current_user` e `current_organization` funcionarem sem o `core` importar um módulo. É
    privilégio de kernel: um app de negócio consome `CurrentUserDep`/`CurrentOrganizationDep`
    e pronto."""

    set_user_reader_factory(SqlAlchemyUserReader)
    set_organization_reader_factory(SqlAlchemyOrganizationReader)

    app.include_router(auth_router, prefix="/api")
    app.include_router(access_router, prefix="/api")
