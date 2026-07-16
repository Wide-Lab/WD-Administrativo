from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import mount_routes
from src.core.config import get_config
from src.core.database.startup import get_database
from src.core.exceptions import AppError
from src.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    config = get_config()
    setup_logging(config.LOG_LEVEL)
    yield
    await get_database().dispose_engine()


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_config().CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Traduz os erros de aplicação do `core` em resposta HTTP. Sem isto, um
    `UnauthorizedError` viraria 500 em vez de 401."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "details": exc.details},
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Superapp Widelab",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    setup_middleware(app)
    setup_exception_handlers(app)

    api = APIRouter()
    mount_routes(api)
    app.include_router(api, prefix="/api")

    return app


app = create_app()
