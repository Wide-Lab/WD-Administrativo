# Backend — Superapp Widelab

FastAPI hexagonal por módulo, Postgres async, Alembic. Fonte da verdade: `../.claude/specs`
(comece por `backend/01-fundacao.md`).

## Dev local

```bash
docker compose up -d db          # sobe o Postgres
cp .env.example .env             # ajuste DATABASE_URL se necessário
uv sync                          # instala dependências
uv run alembic upgrade head      # aplica migrations
uv run uvicorn src.main:app --reload   # sobe em :8000  (GET /api/health)
```

## Qualidade

```bash
uv run ruff format .
uv run ruff check .
uv run mypy src
```
