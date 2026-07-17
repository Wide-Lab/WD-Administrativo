---
name: verify
description: Use when the user asks to verify, check, lint, typecheck, or run the tests/quality gate for the Superapp Widelab (apps/administrativo) — e.g. "roda os testes", "passa o lint", "verifica se está tudo verde", "typecheck do frontend".
---

# Verify

Roda as verificações estáticas e a suíte do Superapp Widelab. Rode o que for da ponta que você
mexeu; antes de fechar uma entrega, rode as duas pontas. **Passar aqui não é o mesmo que uma
spec estar implementada** — critério de aceite se observa rodando o sistema (ver
`implementar-spec`), não só ficando verde no lint.

## Backend (de `backend/`, via `uv run`)

```bash
uv run ruff check .          # lint
uv run mypy src tests        # typecheck — cobre a suíte também (disallow_untyped_defs)
uv run pytest                # a suíte inteira — EXIGE Docker rodando
uv run pytest tests/unit     # só a regra pura (mapa papel→permissão) — SEM Docker
uv run pytest -k entitlement # um recorte
```

- **`pytest` exige Docker Desktop no ar.** A suíte sobe um Postgres efêmero (testcontainers,
  porta efêmera) e migra com `alembic upgrade head`. Sem Docker, ela falha na hora com mensagem
  clara — não é erro de rede.
- **Ela ignora seu `DATABASE_URL` de propósito.** Mesmo com a variável exportada apontando pra
  outro banco, a suíte roda contra o container dela e não toca o banco do shell. Você não
  precisa (nem deve) preparar banco, migration ou `.env` pra rodá-la.
- `tests/unit` roda em ~0,04s sem Docker; é onde o mapa papel→permissão fica preso. Use-o pra
  loop rápido quando a mudança é de regra pura.
- **Teste não é opcional no backend:** todo critério de aceite testável entra em
  `backend/tests/` na mesma entrega (`backend/07-testes.md`). Verificar backend inclui um
  `pytest` verde, não só lint + typecheck.

Se um `uv run` falhar **baixando pacote** (`proxy authorization required`), é o proxy desta
máquina — prefixe `NO_PROXY='*' uv sync` uma vez. `ruff`/`mypy`/`pytest` não tocam a rede.

## Frontend (de `frontend/`, via `npm`)

```bash
npm run typecheck            # tsc --noEmit (strict)
npm run lint                 # next lint (ESLint)
npm run test                 # vitest run — só as libs puras (nav, home-path, schema de senha)
npm run build                # build de produção
```

`npm run test` cobre **só regra pura** (61 testes): não há testing-library/jsdom, então casca,
guards, `Can`, seletor e os formulários de onboarding **não têm teste** — é a dívida de teste
do frontend, deixada em aberto de propósito. Verde aqui não cobre componente.

## NÃO rode `npm run format` nem `npm run check`

`npm run format` (`prettier --write .`) e `npm run check` (`prettier --check .`) tocam o **repo
inteiro**, e ~12 arquivos intocados estão em CRLF no disco (autocrlf do Git no Windows, sem
`.gitattributes`). Consequência:

- `npm run format` reescreve o fim de linha do projeto todo e **afoga a entrega num diff de
  milhares de linhas** que não são a sua mudança.
- `npm run check` fica **vermelho por causa desses arquivos herdados** — um vermelho que não
  significa que o seu código está mal formatado.

Formate **só os arquivos da sua entrega**, preservando o EOL de cada um:

```bash
npx prettier --write --end-of-line auto <seus-arquivos>
```

Pra saber se um `--check` vermelho é seu ou herdado, compare com o baseline (`git stash` +
`--check`). Consertar de vez é um `.gitattributes` — dívida de infra, commit/spec próprio,
separado de qualquer feature.

## Reportar

Diga o que passou e o que não passou, comando por comando. Se algo não pôde rodar (ex.: sem
Docker pra `pytest`, sem browser pra critério visual), diga isso explicitamente — não declare
"tudo verde" genérico.
