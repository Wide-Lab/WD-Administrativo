---
name: run
description: Use when the user asks to run, start, boot, or bring up the Superapp Widelab (apps/administrativo) locally — the stack, the backend, the frontend, or the database — e.g. "sobe o backend", "roda a app", "start the frontend", "levanta a stack".
---

# Run

Sobe o Superapp Widelab nesta máquina. O scaffold já existe (backend FastAPI, frontend Next,
`docker-compose.yml`), então os comandos abaixo valem — mas o ambiente do Kauan (Windows +
Git Bash + proxy de sistema + um Postgres de outro projeto em `localhost:5432`) tem armadilhas
que não estão no repositório. Elas estão embutidas aqui.

## Escolha o caminho primeiro

| Quero…                                     | Caminho                                                    |
| ------------------------------------------ | --------------------------------------------------------- |
| A stack inteira, do jeito que roda em prod | **Compose** — tudo atrás do nginx, sem tocar em porta     |
| Iterar no backend com `--reload`           | **Backend nativo** — precisa do forwarder de Postgres     |
| Iterar no frontend com HMR                 | **Frontend nativo** — `npm run dev`, fala com o backend   |

Na dúvida, **Compose** é o caminho sem surpresa: não depende de porta de Postgres nem de
`JWT_SECRET_KEY` inline.

## Compose — a stack inteira

De `apps/administrativo/`:

```bash
docker compose up            # sobe db + backend + frontend + nginx
```

Tudo responde atrás do nginx na porta `${PORT}` do `.env`. O `db` fica numa rede `internal`
e **não publica porta** de propósito — é por isso que o backend nativo não o alcança (ver
abaixo). Não há passo de migration manual: o backend roda contra o schema que o Alembic já
aplicou; se for banco novo, rode `alembic upgrade head` dentro do container do backend.

`docker compose up db` sobe **só** o Postgres, mas — repito, porque o CLAUDE.md sugere o
contrário — ele fica inalcançável de um processo nativo sem o forwarder. Use isso só junto do
caminho nativo abaixo.

## Backend nativo (`--reload`) — e o Postgres que não está onde parece

**Nunca confie no `backend/.env` para rodar nativo.** Ele aponta pra
`postgresql+asyncpg://…@localhost:5432/…`, e nesta máquina **`localhost:5432` é o Postgres de
OUTRO projeto** (o `db` deste compose é `internal`, sem porta publicada). Rodar `alembic` ou
`uvicorn` nativo com o `.env` como está **escreve/migra o banco errado, sem dar erro**. O
`.env` também **não tem `JWT_SECRET_KEY`**, que o `Config` exige.

Suba um forwarder pro container deste projeto e aponte a `DATABASE_URL` pra ele:

```bash
docker compose up -d db      # sobe o db deste projeto (administrativo-db-1)
docker run -d --name pgfwd -p 15432:5432 alpine/socat \
  tcp-listen:5432,fork,reuseaddr tcp-connect:administrativo-db-1:5432
docker network connect administrativo_db-internal pgfwd
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:15432/administrativo"
export JWT_SECRET_KEY="dev-secret-nao-use-em-prod"
```

Depois, de `backend/`:

```bash
uv run alembic upgrade head                      # schema (só via Alembic, nunca create_all)
uv run uvicorn src.main:app --reload             # sobe em :8000
```

Inspecionar o banco direto:
`docker exec -i administrativo-db-1 psql -U postgres -d administrativo`.

## Frontend nativo (HMR)

De `frontend/`:

```bash
npm run dev                  # :3000, com rewrite /api/* -> backend
```

Precisa do backend no ar (nativo ou via compose) pra `/api/*` responder.

## Reiniciar / liberar porta — no Windows, `pkill` MENTE

`pkill -f uvicorn` no Git Bash **retorna sucesso sem matar nada**: o processo velho segue
segurando a porta, o `uvicorn` novo falha no bind (`[Errno 10048]`), morre — e como o velho
continua respondendo, tudo *parece* no ar enquanto serve **código velho**. Mate por PID e
**confirme a porta livre** antes de subir de novo (PowerShell):

```powershell
netstat -ano | Select-String ":8000.*LISTENING"   # pega o PID
taskkill /F /PID <pid>
```

Sinal de alerta: se o log do uvicorn novo mostrar `error while attempting to bind`, quem
responde é o processo velho.

## Se um comando `uv` falhar baixando pacote

Só ao **instalar** (`uv sync`, `uv add`): esta máquina tem proxy de sistema que exige auth, e
o `uv` o herda e falha com `proxy authorization required`. `curl` funcionar não significa que
o `uv` vai — prefixe `NO_PROXY='*'`:

```bash
NO_PROXY='*' uv sync
```

`uv run uvicorn/pytest/ruff/mypy` **não** precisam disso — não tocam a rede.

## Pré-requisitos

Docker Desktop rodando (o compose e o forwarder dependem dele). `uv` no backend, Node ≥20 no
frontend. A verificação (lint/typecheck/testes) é a skill **`verify`**, não esta.
