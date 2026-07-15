from fastapi import FastAPI


def mount_routes(app: FastAPI) -> None:
    """Registra os routers dos módulos no router `/api`. Adicionar um módulo é uma linha
    aqui — `api.include_router(<modulo>_router)` — sem tocar em mais nada do `core`.

    Na fundação não há módulo: `src/modules/` está vazio."""

    return None
