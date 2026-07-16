from fastapi import FastAPI

from src.core.security import set_user_reader_factory
from src.modules.auth.adapters.db.user_reader import SqlAlchemyUserReader
from src.modules.auth.adapters.http.routes import router as auth_router


def mount_routes(app: FastAPI) -> None:
    """Registra os routers dos módulos no router `/api`. Adicionar um módulo é uma linha
    aqui — `app.include_router(<modulo>_router, prefix="/api")` — sem tocar em mais nada do
    `core`.

    O `auth` é kernel e tem uma linha a mais: ele entrega ao `core` a implementação de
    `UserReader`, e é isso que deixa `current_user` funcionar sem o `core` importar `auth`."""

    set_user_reader_factory(SqlAlchemyUserReader)

    app.include_router(auth_router, prefix="/api")
