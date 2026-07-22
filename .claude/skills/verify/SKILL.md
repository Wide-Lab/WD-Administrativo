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
  `backend/tests/` na mesma entrega (`backend/07-testes/spec.md`). Verificar backend inclui um
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

`npm run test` cobre **só regra pura** (180 testes em 14 arquivos, medidos em 2026-07-22): não há
testing-library/jsdom, então casca, guards, `Can`, seletor, os formulários de onboarding e as seis
telas das `frontend/07`/`08` **não têm teste de DOM** — é a dívida de teste do frontend, deixada em
aberto de propósito (ver `Fases` na `00-visao-geral.md`). Verde aqui não cobre componente.

## `npm run check` pode rodar — a dívida de CRLF foi paga

```bash
npm run check                # prettier --check . — verde no repo inteiro
```

Até 2026-07-22 esta seção dizia o contrário, e com razão: sem `.gitattributes`, 261 arquivos
intocados estavam em CRLF no disco, o `--check` ficava vermelho por causa deles e o `--write`
afogava a entrega num diff de milhares de linhas. **Isso acabou:** o `.gitattributes` na raiz
fixa `text=auto` e o `frontend/.prettierrc.json` ganhou `"endOfLine": "auto"`, então o prettier
parou de brigar com o fim de linha do working tree. Não precisa mais de `--end-of-line auto` na
mão, e um `--check` vermelho agora **é seu** — trate como erro de verdade.

`npm run format` continua merecendo cuidado, mas por outro motivo: ele roda `eslint --fix .` no
repo inteiro junto do prettier. Se quiser só formatar a sua entrega, `npx prettier --write
<seus-arquivos>` continua sendo o caminho mais previsível.

## Reportar

Diga o que passou e o que não passou, comando por comando. Se algo não pôde rodar (ex.: sem
Docker pra `pytest`, sem browser pra critério visual), diga isso explicitamente — não declare
"tudo verde" genérico.
