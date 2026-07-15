# 01 — Fundação do backend

**Depende de:** nada dentro do backend.
**Entrega:** um projeto FastAPI que sobe, conecta no Postgres, expõe `GET /health`, tipa e
linta — com a estrutura de pastas que todo módulo futuro (identidade, organizações, membros,
e mais tarde os apps Refeições e Carro) vai seguir.

## Objetivo

Montar o esqueleto do backend do superapp seguindo a convenção hexagonal da casa (Central /
`receipt-reader`), com dois ajustes já combinados na `00-visao-geral.md`:

- Nomes de tabela são `snake_case` no plural, **sem** o prefixo `T0xx` da Central.
- O núcleo é desenhado pra multi-tenancy e autorização (ao contrário da Central, que
  _"autentica, não autoriza"_) — mas esta spec **não** implementa tenancy nem papéis; só
  deixa `core` pronto pra recebê-los nas specs 02–04.

## Fora de escopo

Qualquer módulo de negócio ou de plataforma. Esta spec entrega a casca — `core`, `api`, a
convenção de módulo — com `src/modules/` **vazio**. Identidade é da `02`, organizações da
`03`, membros/autorização da `04`. Nada de login, sessão, `Organization` ou `Membership`
aqui.

## Stack

| Papel                  | Escolha                        |
| ---------------------- | ------------------------------ |
| Framework              | FastAPI                        |
| Servidor ASGI          | Uvicorn                        |
| ORM                    | SQLAlchemy 2 (async)           |
| Driver Postgres        | `asyncpg`                      |
| Migrations             | Alembic                        |
| Config                 | `pydantic-settings`            |
| Gerenciador de pacotes | `uv`                           |
| Qualidade              | `ruff` (lint + format), `mypy` |

Python >= 3.14, como na Central.

### Dependências

```
fastapi[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic-settings
```

> Config e carga do `.env` são **só** via `pydantic-settings`
> (`SettingsConfigDict(env_file=".env")`, como em `core/config.py`) — **sem** `python-dotenv`,
> que seria redundante.
>
> `uvicorn` é fixado explicitamente no `pyproject` (a app sobe com `uvicorn src.main:app`),
> ainda que `fastapi[standard]` já o inclua.

Dev:

```
ruff
mypy
```

> As dependências de autenticação (`argon2-cffi`, `pyjwt`) chegam na `02-identidade-e-sessao.md`,
> não aqui — `core/security.py` nasce como placeholder.

## Estrutura de pastas

```
backend/
  migrations/
    versions/
    env.py
  src/
    main.py                # cria o FastAPI, lifespan, CORS, monta rotas
    api/
      routes.py             # mount_routes(app) — um include_router por módulo
    core/
      config.py             # Config (pydantic-settings), get_config()
      database/             # infra de banco (pacote)
        base_model.py        # Base(DeclarativeBase)
        database.py          # dataclass Database (engine + sessionmaker)
        startup.py           # create_engine/sessionmaker + get_database() (factory @lru_cache)
        types.py             # Protocol Engine
        unit_of_work.py      # SQLAlchemyUnitOfWork
        repositories/
          sqlalchemy_base.py  # repositório assíncrono genérico (base dos módulos)
      security/             # primitivos de segurança (pacote)
        passwords.py         # hasher de senha — Argon2id
        jwt.py               # encoder/decoder de token — pyjwt
      exceptions.py         # AppError + hierarquia (NotFound, Conflict, Unauthorized, …)
      logging.py
    modules/
      <modulo>/
        domain/              # entidades e regras puras — sem import de framework
        application/
          use_cases/
          dtos/
        adapters/
          db/                 # models.py (ORM) + repository.py
          http/
            routes.py
            dependencies/
              providers.py     # factories injetadas via Depends
              types.py         # Annotated[...] compartilhados
  pyproject.toml
  alembic.ini
  Dockerfile
  .env.example
```

**Regra que não se negocia (é o _seam_ de extração da `00-visao-geral.md`):** dentro de um
módulo, tudo que fala com o mundo externo (HTTP, banco) mora em `adapters/`. `domain/` não
importa nada de `application/`, `adapters/`, FastAPI ou SQLAlchemy. `application/` importa
`domain/`, nunca `adapters/` diretamente — recebe repositórios como argumento, injetados
pelas dependencies de `adapters/http/`. **Um módulo nunca importa outro módulo**; se dois
módulos precisam conversar, é via `core` ou via porta explícita. Adicionar um módulo novo
**não pode tocar `src/core`** — só ganha uma linha em `mount_routes`.

## Convenção de nomes de tabela

`snake_case` no plural, sem prefixo. Sem `T0xx`. Exemplos que as próximas specs vão criar:
`users`, `organizations`, `memberships`, `module_entitlements`, `partner_agreements`. Chave
primária `id` (UUID). Toda tabela de negócio ganha, nas specs 03+, uma coluna de escopo de
tenant (`organization_id` ou equivalente) — mas isso é decisão da `03`, não desta spec.

## `src/core/config.py`

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = []


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()  # type: ignore
```

## `src/core/database/` (pacote)

Padrão trazido do backend `seifert`, **não** o `_DataBase` singleton da Central:

- `base_model.py` — `Base(DeclarativeBase)`, base ORM de todos os models.
- `types.py` — `Protocol Engine` (só o que a app usa do engine: `dispose()`).
- `database.py` — dataclass `Database` (engine + `async_sessionmaker`) com `create_session()`
  e `dispose_engine()`.
- `startup.py` — `create_engine`/`create_sessionmaker` + `get_database()` (factory
  `@lru_cache`). **Não há `db.init()`** — a instância nasce preguiçosamente no `get_database()`.
- `unit_of_work.py` — `SQLAlchemyUnitOfWork` (commit/rollback; mapeia `IntegrityError` →
  `ConflictError`).
- `repositories/sqlalchemy_base.py` — repositório assíncrono genérico (`get_by_id`, `create`,
  `update`, `delete`, `paginate`), base dos repositórios dos módulos.

O repositório genérico e a paginação dependem de tipos de comando/sentinela compartilhados e
de um módulo de paginação. Ao portar de `seifert`, **traga junto** `core/types` (comandos
`BaseCreateCommand`/`BaseUpdateCommand`, sentinela `UNSET`, `DataclassInstance`) e
`core/pagination` (`Page`/`PageParams`) — sem eles, `repositories/sqlalchemy_base.py` não
importa.

## `src/core/security/` (pacote)

Os primitivos de segurança **já entram na fundação** (o módulo `auth` da spec 02 constrói
sessão e `current_user` em cima deles). Os algoritmos são **decisão travada**
(`00-visao-geral.md` e `backend/02`):

- `passwords.py` — hasher **Argon2id** (`argon2-cffi`), nunca bcrypt.
- `jwt.py` — encoder/decoder de token com **pyjwt** (`pyjwt[crypto]`), não python-jose.

Isso adianta as dependências `argon2-cffi` e `pyjwt[crypto]` (antes previstas só na spec 02),
já que os primitivos aterrissaram aqui.

## `src/core/exceptions.py`

`AppError` base (com `status_code`, `code`, `message`, `details`) e a hierarquia que os
adapters HTTP traduzem em resposta: `NotFoundError` (404), `ConflictError` (409),
`UnauthorizedError` (401), `ForbiddenError` (403), `ValidationAppError` (422),
`PersistenceError` (500).

## `src/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import mount_routes
from src.core.config import get_config
from src.core.database.startup import get_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await get_database().dispose_engine()


app = FastAPI(lifespan=lifespan, root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_config().CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


mount_routes(app)
```

`root_path="/api"` casa com o contrato do frontend: o nginx (prod) e o rewrite do Next (dev)
roteiam `/api/*` pra cá — ver `frontend/01-fundacao.md`.

**`allow_origins` nunca pode ser `"*"`.** A sessão depende de credenciais
(`allow_credentials=True`), e o navegador rejeita origem coringa com credenciais.
`CORS_ORIGINS` lista explicitamente as origens autorizadas via `.env` (em dev, a origem do
Next; em prod, os domínios dos tenants).

## Schema via Alembic, não `create_all`

Toda mudança de schema nasce como `uv run alembic revision --autogenerate -m "..."`, e o
deploy roda `uv run alembic upgrade head` antes de subir o servidor. Sem
`Base.metadata.create_all`, nem em dev.

## Ambiente local

`docker-compose.yml` sobe pelo menos o Postgres (`docker compose up db`); backend roda
nativo via `uv`, apontando `DATABASE_URL` pra `localhost:5432`. A stack completa (Postgres +
backend + frontend + nginx) segue o mesmo desenho da Central e é detalhada quando o frontend
existir — não é requisito desta spec.

## Scripts (via `uv run`)

| Comando                                    | Ação                              |
| ------------------------------------------ | --------------------------------- |
| `uvicorn src.main:app --reload`            | sobe em desenvolvimento (`:8000`) |
| `ruff format .`                            | formata                           |
| `ruff check .`                             | lint                              |
| `mypy src`                                 | typecheck                         |
| `alembic revision --autogenerate -m "msg"` | gera migration                    |
| `alembic upgrade head`                     | aplica migrations                 |

## Critérios de aceite

1. `uv run uvicorn src.main:app --reload` sobe e `GET /api/health` responde `{"status": "ok"}`.
2. `uv run alembic upgrade head` roda sem erro contra um Postgres vazio.
3. `uv run ruff check .` e `uv run mypy src` passam num checkout limpo.
4. `src/modules/` existe e está vazio — nenhum módulo nesta spec.
5. Adicionar um módulo novo seguindo `domain/`, `application/`, `adapters/{db,http}` não
   exige tocar em `src/core`, além de uma linha em `mount_routes`.
6. Nenhuma tabela é criada fora de migration, e nenhum nome de tabela usa prefixo `T0xx`.
