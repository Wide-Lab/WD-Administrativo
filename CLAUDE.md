# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Superapp Widelab (`apps/administrativo`)

Plataforma web **multi-tenant** que hospeda vários serviços internos ("apps") sob um mesmo
núcleo de identidade, organizações e permissões. Nasce pra resolver dores internas da Widelab
(controle de refeições e de uso da frota) e é construída pra ser **vendida** a outras
empresas. Backend FastAPI + frontend Next, monólito modular.

## A fonte da verdade é `.claude/specs/`, não este arquivo

Antes de implementar qualquer coisa não trivial, leia `.claude/specs/00-visao-geral.md`
inteiro e a spec numerada relevante. As specs registram não só o *quê*, mas o **porquê**, o
que foi decidido **não** fazer ainda, e critérios de aceite explícitos. Este `CLAUDE.md` é um
mapa de navegação rápida — quando ele e uma spec discordarem, **a spec vence**.

| # | Backend | | Frontend | |
|---|---|---|---|---|
| 01 | fundação (FastAPI hexagonal) | ✅ | fundação (Next App Router) | ✅ |
| 02 | identidade e sessão (`auth`) | ✅ | design system | ✅ |
| 03 | organizações e tenancy (`access`) | ⬜ | login e sessão | ✅ |
| 04 | membros e autorização (`access`) | ⬜ | casca e personas | ⬜ |
| 05 | módulos e entitlements (`access`) | ⬜ | seleção de organização | ⬜ |
| 06 | convites e onboarding (`access`) | ⬜ | onboarding | ⬜ |

**Use a skill `nova-spec`** pra propor uma spec nova e **`implementar-spec`** pra executar
uma existente — ambas seguem o formato da casa (`Depende de` / `Entrega` / `Objetivo` /
`Fora de escopo` / `Critérios de aceite`).

## Estado atual — kernel `auth` de ponta a ponta; `access` ainda não existe

Backend `01`–`02` e frontend `01`–`03` estão implementados: dá pra subir a stack, logar com
e-mail+senha e manter sessão. **A próxima entrega é `backend/03-organizacoes-e-tenancy.md`**
(`Organization`, escopo por tenant, convênio), que destrava frontend `04`.

O que existe hoje:

- `backend/` — `src/core` (config, database, security, exceptions, logging, pagination,
  types) + `src/modules/auth/` completo: login, logout, `GET /api/me`, `PUT /api/me/password`,
  CLI de bootstrap, migration `0001_users`.
- `frontend/` — scaffold Next, design system (tokens em `src/styles.css`, primitivos shadcn,
  vitrine em `/design-system`), feature `auth` (`/entrar`, `use-session`, guarda de rota) e
  uma `/` autenticada **placeholder** — a home de verdade é decidida por frontend `04`.
- `docker-compose.yml` + `nginx/` — stack completa (Postgres, backend, frontend, nginx).
- `src/modules/access/`, os route groups por persona (`(admin)`/`(parceiro)`/`(colaborador)`)
  e qualquer app de negócio **não existem ainda**. Não assuma — confirme lendo o diretório.

## Arquitetura (o retrato grande, que exige ler várias specs)

- **Monólito modular multi-tenant.** Um backend, um frontend, um Postgres. A unidade de
  deploy é o container, não o módulo. *Seams* de extração desenhados, não usados
  (`00-visao-geral.md`).
- **Kernel da plataforma = dois módulos:** `auth` (identidade/sessão) e `access` (organizações,
  membros, autorização, entitlements, onboarding). Os **apps de negócio** (`refeicoes`,
  `frota`) plugam depois e dependem **só** de `core` + dos *contracts* públicos do kernel —
  `current_user`, `current_organization`, `require_permission`, `require_module` — e **nunca
  um do outro**. É isso que mantém o seam de extração limpo.
- **Autorização é o núcleo** — o oposto da Central (`autentica, não autoriza`). Empresa,
  Parceiro, Colaborador e papéis são o produto.
- **Tenant no path:** todo dado é escopado por organização; a org ativa viaja em
  `/api/organizacoes/{orgId}/...`, nunca em header nem sessão. Escopo por linha
  (`organization_id`), banco/schema compartilhados.
- **Entitlement por tenant:** cada Empresa só enxerga os módulos que contratou; negação por
  padrão; imposto no backend com `require_module` → 403, não só escondido no frontend.
  Vender um módulo é ligar um flag, sem deploy.
- **Identidade própria atrás de porta trocável:** login local agora (`PasswordAuthenticator`);
  SSO da Central (JWT RS256/JWKS) plugável depois sem tocar autorização.
- **Frontend:** uma app Next só; personas (Admin da Empresa / Parceiro / Colaborador /
  Plataforma) resolvidas de `GET /api/organizacoes/{orgId}/eu`; navegação derivada dos
  módulos habilitados. Trocar de organização é navegar pra outro `orgId`.

## Convenções que não se negociam

- **Backend hexagonal:** `src/core` intocável por módulos; `modules/<mod>/` em camadas
  (`domain` → `application` → `adapters`); `application` recebe repositório via `Depends`,
  nunca importa `adapters`; **módulo não importa módulo**; adicionar módulo é uma linha em
  `mount_routes`, sem tocar `core`.
- **`core` nunca importa módulo — a seta aponta pra dentro.** Quando o `core` precisa de algo
  que um módulo é dono (ex.: `current_user` precisa ler `users`, tabela do `auth`), o `core`
  declara uma **porta** (`UserReader`, em `core/security/identity.py`) e o módulo **registra a
  implementação** em `mount_routes` (`set_user_reader_factory(SqlAlchemyUserReader)`). É o
  único caso em que um módulo ganha uma segunda linha no `mount_routes` — privilégio de
  kernel, não de app de negócio.
- **Schema só via Alembic**, sem `create_all`. Nomes de tabela `snake_case` no plural, **sem**
  prefixo `T0xx`. E-mail é `CITEXT`; senha é **Argon2id**, nunca bcrypt.
- **Rotas em português; tenant no path.** `/api/me*` é o usuário global; `/api/organizacoes/{orgId}/eu`
  é "eu nesta organização". Nomes de tabela, coluna e valores de enum seguem em **inglês**.
- **Organização tem um tipo só** (`platform`/`company`/`partner`), definido na criação e
  **imutável**; a integridade dos lados do convênio é garantida no banco (FK composta), ver
  `backend/03`.
- **Sessão:** JWT assinado pela app (HS256) em cookie httpOnly; **sem papel ou organização no
  token** — isso muda por request e é resolvido pelo `access`.
- **Frontend:** TypeScript strict; **TanStack Query** com fetch client-side; **zod** com tipos
  sempre `z.infer` (nunca à mão); shadcn/Radix; estrutura por `features/<domínio>`; alias
  `#/*` → `./src/*`; componente de domínio mora em `features/<domínio>/components`, nunca solto.
- **Cor só por token.** O hex mora **só** no bloco de paleta de `frontend/src/styles.css`
  (`--palette-*`), mapeado pras utilidades por `@theme inline`. Tela nenhuma usa hex solto nem
  cor do Tailwind (`bg-slate-900`) — use as utilidades de token (`bg-surface`, `text-muted`,
  `ring-ring`). Ver `frontend/02-design-system.md`.

## Comandos

Definidos em `backend/01-fundacao.md` e `frontend/01-fundacao.md`; o scaffold existe, então
eles valem. `docker compose up db` sobe só o Postgres (backend/frontend rodam nativos em dev);
`docker compose up` sobe a stack inteira atrás do nginx.

| Backend (de `backend/`, via `uv run`) | |
|---|---|
| `uvicorn src.main:app --reload` | sobe em dev (`:8000`) |
| `ruff format .` / `ruff check .` / `mypy src` | formata / lint / typecheck |
| `alembic revision --autogenerate -m "msg"` / `alembic upgrade head` | migration |
| `python -m src.modules.auth.cli create-user --email … --name …` | cria usuário (bootstrap) |

| Frontend (de `frontend/`, via `npm`) | |
|---|---|
| `run dev` | sobe em dev (`:3000`, rewrite `/api/*` → backend) |
| `run typecheck` / `run lint` / `run test` | tsc / ESLint / Vitest |
| `run build` | build de produção |

## Skills deste projeto

- **`nova-spec`** — escreve uma spec nova em `.claude/specs/` no formato da casa.
- **`implementar-spec`** — implementa uma spec existente e confere cada critério de aceite.
- **`run`** e **`verify`** ainda **não existem** aqui: use as skills globais `/run` e
  `/verify`, que fazem bootstrap ao ver o projeto pela primeira vez. O scaffold já existe,
  então **criar as versões deste projeto está destravado** — é dívida em aberto.

## Relação com a Central de Aplicações (`apps/central`)

O superapp herda as **convenções** da Central (hexagonal, Postgres async, feature-based, specs
no formato da casa) mas rejeita a **topologia** dela (federação por subdomínio, `autentica não
autoriza`) — situações opostas, ver `00-visao-geral.md`. No futuro, o superapp vira **consumidor
do SSO da Central** via a porta de autenticação (`backend/02`), sem reescrever autorização.
