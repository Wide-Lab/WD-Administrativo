from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import mount_routes
from src.core.config import get_config
from src.core.database.startup import get_database
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


def create_app() -> FastAPI:
    app = FastAPI(
        title="Superapp Widelab",
        lifespan=lifespan,
        root_path="/api",
    )

    setup_middleware(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_routes(app)

    return app


app = create_app()
