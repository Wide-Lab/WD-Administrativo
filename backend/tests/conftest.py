"""O harness da suíte: um Postgres efêmero por sessão, migrado por `alembic upgrade head`.

**Nada aqui importa `src.main` no topo do módulo, e isso é estrutural, não estilo.**
`src/main.py` faz `app = create_app()` no import, e `create_app()` lê `get_config()`, que é
`lru_cache(maxsize=1)`. Um import no topo congelaria a config **antes** de a fixture
`database_url` sobrescrever `DATABASE_URL` com a URL do container — e a suíte rodaria contra o
que o shell exportar. O `.env` deste repo aponta pra um `localhost:5432` que é de **outro
projeto**, então isso não é hipótese: é o acidente que o critério 2 da spec 07 existe pra
impedir. O import tardio, dentro de `_new_client`, é o que o impede.

`src.main` é o **único** import perigoso — o resto de `src` só define, não lê config —, e é por
isso que factories e models entram aqui em cima normalmente.

Pela mesma razão o container **não** sobe no import deste módulo: quem o quer é quem depende de
`database_url`. É isso que deixa `pytest tests/unit` rodar sem Docker (spec 07, "Comandos")."""

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any, Protocol

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config as AlembicConfig
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from tests.factories import (
    DEFAULT_PASSWORD,
    get_platform_organization,
    make_membership,
    make_user,
)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

POSTGRES_IMAGE = "postgres:17-alpine"

TEST_JWT_SECRET_KEY = "chave-de-teste-que-nao-vale-em-lugar-nenhum"

BASE_URL = "https://testserver"
"""`https`, e não `http`, porque o cookie de sessão nasce `Secure` (`SESSION_COOKIE_SECURE`
default `True`). Sobre `http` o httpx **descartaria** o cookie em silêncio, e todo teste
autenticado daria 401 pelo motivo errado. Não há rede aqui — o esquema só decide o que o jar
aceita guardar, e testar com o cookie de produção é o ponto."""

_DOCKER_AUSENTE = (
    "Não foi possível subir o Postgres de teste: o Docker precisa estar rodando.\n"
    "A suíte fala com Postgres de verdade porque as invariantes deste backend moram no banco "
    "(o CHECK gerado, as FKs compostas, o CITEXT) — nenhuma delas é um if em Python, e mock ou "
    "SQLite passariam verdes testando nada.\n"
    "Suba o Docker Desktop e rode de novo, ou rode só a regra pura: uv run pytest tests/unit"
)


def _upgrade_head() -> None:
    """`alembic upgrade head` num banco vazio — o schema da suíte sai daqui, e não de um
    `create_all`. É o que prende as migrations junto: uma migration quebrada derruba a suíte
    inteira, não só o teste que tocaria naquela tabela.

    Roda numa thread (ver quem chama) porque `migrations/env.py` faz `asyncio.run()`, que estoura
    se já houver event loop rodando — e quem a chama é uma fixture async."""

    config = AlembicConfig(str(_BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def _container() -> Iterator[str]:
    """Sobe o Postgres descartável e devolve a URL efêmera.

    Testcontainers, e não um serviço em porta fixa no compose: a máquina de dev já tem outro
    projeto em `localhost:5432`, e uma suíte que roda migration no banco errado falha caro e em
    silêncio. Porta efêmera devolvida pro processo faz "a suíte nunca aponta pro banco errado"
    virar estrutura, e não regra pra alguém lembrar."""

    from testcontainers.postgres import PostgresContainer

    # O `try` cobre a **construção** junto do `start()`, e não só o `start()`: o
    # `PostgresContainer(...)` já fala com o daemon pra resolver o client. Sem Docker, é ali que
    # estoura — e sem esta linha o desenvolvedor recebia um dump de HTML de proxy no lugar de uma
    # frase. Critério 8 da spec 07.
    try:
        container = PostgresContainer(POSTGRES_IMAGE, driver="asyncpg")
        container.start()
    except Exception as exc:
        raise RuntimeError(
            f"{_DOCKER_AUSENTE}\n\nO Docker respondeu: {type(exc).__name__}."
        ) from None

    try:
        yield container.get_connection_url()
    finally:
        container.stop()


@pytest.fixture(scope="session")
async def database_url(_container: str) -> AsyncIterator[str]:
    """A URL do container — já plugada na app, com o schema migrado.

    Ela **sobrescreve** `os.environ["DATABASE_URL"]`, e não usa `setdefault`: o valor do shell é
    exatamente o perigo. Depois disso limpa os `lru_cache` que congelam config, engine e o
    encoder de JWT, pra ninguém herdar uma leitura anterior."""

    from src.core.config import get_config
    from src.core.database.startup import get_database
    from src.core.security.startup import get_jwt_encoder

    os.environ["DATABASE_URL"] = _container
    os.environ["JWT_SECRET_KEY"] = TEST_JWT_SECRET_KEY

    get_config.cache_clear()
    get_database.cache_clear()
    get_jwt_encoder.cache_clear()

    await asyncio.to_thread(_upgrade_head)

    yield _container

    await get_database().dispose_engine()
    get_config.cache_clear()
    get_database.cache_clear()
    get_jwt_encoder.cache_clear()


@pytest.fixture(scope="session")
async def platform_seed(database_url: str) -> dict[str, Any]:
    """A organização `platform` como a migration `0002` a semeou, fotografada uma vez.

    É um snapshot, e não uma constante repetida na suíte, porque o dado é da migration: se o seed
    mudar, o reseed do `clean_database` segue junto sem ninguém lembrar de editar o teste."""

    from src.core.database.startup import get_database
    from src.core.tenancy import OrganizationType

    async with get_database().create_session() as session:
        result = await session.execute(
            sa.select(OrganizationModel).where(OrganizationModel.type == OrganizationType.PLATFORM)
        )
        organization = result.scalars().one()
        return {
            column.name: getattr(organization, column.name)
            for column in OrganizationModel.__table__.columns
        }


@pytest.fixture
async def session(database_url: str) -> AsyncIterator[AsyncSession]:
    """Sessão de banco pras factories e pra conferir no SQL o que a rota afirmou no JSON.

    É a mesma engine da app — e é o `close()` do teardown que solta a transação ociosa, sem a
    qual o `TRUNCATE` do próximo teste ficaria esperando por ela."""

    from src.core.database.startup import get_database

    db_session = get_database().create_session()
    try:
        yield db_session
    finally:
        await db_session.close()


@pytest.fixture
async def plataforma(session: AsyncSession) -> OrganizationModel:
    """A organização `platform`, pros testes que precisam apontar pra ela."""

    return await get_platform_organization(session)


def _new_client() -> AsyncClient:
    """Um cliente httpx falando com a app **em processo**, via ASGI: sem servidor e sem rede.

    O import de `src.main` é aqui dentro, e não no topo — ver o docstring do módulo."""

    from src.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Cliente sem sessão. É com ele que se cobram os 401 e as rotas públicas."""

    async with _new_client() as http_client:
        yield http_client


class Como(Protocol):
    """O contrato da fixture `como` — ver o docstring dela."""

    async def __call__(
        self,
        *,
        role: Role,
        org: OrganizationModel | None = None,
        email: str | None = None,
        password: str = DEFAULT_PASSWORD,
        name: str | None = None,
    ) -> AsyncClient: ...


@pytest.fixture
async def como(session: AsyncSession) -> AsyncIterator[Como]:
    """`como(role=Role.HR, org=empresa)` → um cliente já com o cookie de sessão.

    **É a fixture que decide a ergonomia da suíte**, e é por isso que ela existe. A pergunta que
    este backend responde é sempre a mesma — *"papel X, na organização Y, batendo no endpoint Z:
    200 ou 403?"* — e sem um atalho pra "me dê um cliente autenticado como `hr` na Acme", cada
    teste vira quinze linhas de setup e ninguém escreve o segundo.

    O login é **de verdade**: `POST /api/auth/login`, com a senha em claro, e o cookie vem do
    servidor. Nada de forjar JWT — uma suíte que emite a própria sessão para de cobrir o login e
    fica verde com ele quebrado.

    Sem `org`, o vínculo nasce na organização `platform`: é o atalho pro `platform_admin`."""

    clients: list[AsyncClient] = []

    async def _como(
        *,
        role: Role,
        org: OrganizationModel | None = None,
        email: str | None = None,
        password: str = DEFAULT_PASSWORD,
        name: str | None = None,
    ) -> AsyncClient:
        organization = org if org is not None else await get_platform_organization(session)

        user = await make_user(session, email=email, name=name, password=password)
        await make_membership(
            session,
            user_id=user.id,
            organization=organization,
            role=role,
        )

        http_client = _new_client()
        clients.append(http_client)

        response = await http_client.post(
            "/api/auth/login",
            json={"email": user.email, "password": password},
        )
        assert response.status_code == 200, f"login falhou no setup: {response.text}"

        return http_client

    yield _como

    for http_client in clients:
        await http_client.aclose()
