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
| 03 | organizações e tenancy (`access`) | ✅ | login e sessão | ✅ |
| 04 | membros e autorização (`access`) | ✅ | casca e personas | ✅ |
| 05 | módulos e entitlements (`access`) | ✅ | seleção de organização | ✅ |
| 06 | convites e onboarding (`access`) | ✅ | onboarding | ⬜¹ |

¹ **a próxima entrega.** O backend já convida e aceita, mas ninguém convida pela tela: o
`POST /convites` e o aceite por token não têm UI, e o auto-cadastro de Parceiro também não.

**Use a skill `nova-spec`** pra propor uma spec nova e **`implementar-spec`** pra executar
uma existente — ambas seguem o formato da casa (`Depende de` / `Entrega` / `Objetivo` /
`Fora de escopo` / `Critérios de aceite`).

## Estado atual — kernel completo; falta a tela do onboarding

Backend `01`–`06` e frontend `01`–`05` estão implementados: dá pra subir a stack, logar,
provisionar Empresas/Parceiros, conveniá-los, vincular pessoas com papel, **vender módulo
ligando um flag** — e **o backend nega de verdade** (403 em tenant sem vínculo, 403 em permissão
faltante, 403 em módulo não contratado). Com a `frontend/04`, logar já cai na casca da sua
persona, com a navegação saindo dos módulos que o **tenant** contratou; com a `frontend/05`, quem
tem mais de um vínculo **troca de organização pelo seletor do masthead**, e o pós-login volta pra
última organização visitada. Com a `backend/06`, **entrar no sistema deixou de ser CLI**:
Colaborador é convidado e aceita por token; Parceiro se auto-cadastra. **A próxima entrega é
`frontend/06-onboarding.md`**, que dá tela a esses dois caminhos; no backend, o que resta antes
da fase 2 é a dívida de teste automatizado.

O que existe hoje:

- `backend/` — `src/core` (config, database, security, **tenancy**, **authz**, **modules**,
  **notifications**, exceptions, logging, pagination, types) + `src/modules/auth/` completo:
  login, logout, `GET /api/me`, `PUT /api/me/password`, CLI de bootstrap, migration
  `0001_users`.
- `src/modules/access/` — `organizations` (platform/company/partner), `partner_agreements`
  (convênio), `memberships` (usuário↔org↔papel), `module_entitlements` (Empresa↔módulo) e
  `invitations` (convite↔papel). Rotas: `POST`/`GET /api/organizacoes`,
  `GET /api/organizacoes/{orgId}`, `/convenios` (criar, listar, suspender/reativar),
  `GET /api/me/contexto`, `GET /api/organizacoes/{orgId}/eu`,
  `GET`/`PATCH /api/organizacoes/{orgId}/membros`, `GET`/`PUT`/`DELETE
  /api/organizacoes/{orgId}/modulos[/{chave}]`, `POST /api/organizacoes/{orgId}/convites`, e as
  **públicas** `GET /api/convites/{token}`, `POST /api/convites/{token}/aceitar` e
  `POST /api/parceiros/cadastro`. Migrations `0002_organizations` — que **semeia a organização
  `platform`** (`01890000-0000-7000-8000-000000000001`) —, `0003_memberships`,
  `0004_module_entitlements` e `0005_invitations`.
- **Entrar no sistema são dois caminhos, deliberadamente diferentes** (`backend/06`): o
  Colaborador/staff é **convidado** (`invitations.write` = `company_admin`/`hr`) e aceita por um
  token opaco de **uso único** — que cria o login se não houver, cria o vínculo e emite sessão;
  o Parceiro **se auto-cadastra** (`POST /api/parceiros/cadastro`, público) e a organização, o
  primeiro `partner_admin` e o vínculo nascem **numa transação só**. Convite expirado/revogado/
  já aceito responde **410**; a expiração é derivada de `expires_at`, e `status = 'expired'`
  nunca é gravado. **Não há rota de revogar nem de listar convite**, e **Parceiro não convida** —
  os dois são buracos conhecidos, ver `Como ficou` da `backend/06`.
- **Papéis e permissões são fixos e declarados em código**, em `access/domain/permissions.py`
  (`ROLES_BY_ORGANIZATION_TYPE`, `PERMISSIONS_BY_ROLE`, `persona_for`). Papel só vale no tipo
  de organização certo, e **quem garante é o banco**: `memberships` tem um `organization_type`
  ancorado por FK composta contra `organizations(id, type)` + um `CHECK` **gerado** do mapa do
  domínio. Mexeu no mapa, mexe na migration.
- **Entitlement é presença de linha em `module_entitlements`** — não há coluna de ligado, e
  ausência é negação. Só Empresa contrata, e quem garante é o banco (FK composta contra
  `organizations(id, type)`, tipo fixado em coluna gerada). `require_module` (`core/modules/`)
  nega com 403 e **não afrouxa pra `platform_admin`** — diferente de `require_permission`, a
  pergunta é o que o *tenant* comprou, não quem é o usuário. Só `platform_admin` liga/desliga
  (`modules.read`/`modules.write`).
- **Módulo de negócio pluga com uma linha:** `mount_module(api, <ModuleDescriptor>)` em
  `mount_routes` registra o módulo no `ModuleRegistry` e pendura as rotas sob
  `/api/organizacoes/{orgId}/<chave>/*` já atrás do `require_module` — prefixo e guard não são
  disciplina do módulo. `refeicoes` e `frota` existem só como **chaves registradas** em
  `src/api/modules.py` (placeholder até as fases 2/3; o descritor vai pro módulo quando ele
  existir).
- **Furo conhecido, e é da fase 2:** `ModuleDescriptor.permissions` é declarativo e **não liga
  em nada** — não existe mecanismo que ligue capability de módulo a papel (`PERMISSIONS_BY_ROLE`
  é do `access`, e módulo não importa módulo). O primeiro app de negócio esbarra nisso no
  primeiro endpoint; ganha spec própria. Ver `Como ficou` da `backend/05`.
- **Criar membro é convite** (`POST /api/organizacoes/{orgId}/convites` + aceite), não `POST`
  direto. A **CLI de vínculo continua**, agora só pro que o convite não alcança — o bootstrap do
  primeiro `platform_admin`, que não tem quem o convide, e o segundo membro de um Parceiro:
  `python -m src.modules.access.cli grant --email … --role … [--org …]`; sem `--org`, o alvo é
  a organização `platform`.
- `frontend/` — scaffold Next, design system (tokens em `src/styles.css`, primitivos shadcn,
  vitrine em `/design-system`), feature `auth` (`(publico)/entrar`, `use-session`, guarda de
  rota) e feature `context`: `use-context` (`/api/me/contexto`), `use-org-context`
  (`/eu` + nome da org), `buildNav`/`homePathFor` (puras, testadas), `AppShell`, `Can`,
  `ModuleGuard`, `OrganizationSwitcher` (o seletor do masthead) e `lib/last-org.ts` (o último
  `orgId`, único uso de `localStorage`). Rotas: `/` **roteia** pra home da persona (não é tela), `/plataforma`
  (cross-tenant, guarda por vínculo de plataforma) e `/organizacoes/[orgId]/*`, cujo `layout`
  resolve a persona e monta a casca. `refeicoes`/`frota` existem como **rotas-placeholder atrás
  do `ModuleGuard`** — as fases 2/3 as substituem.
- **A organização ativa é o `orgId` da URL — não há store de "org ativa", e o seletor só navega.**
  O `localStorage` guarda **uma** coisa (`lib/last-org.ts`): o último `orgId` visitado, usado só
  pra decidir o redirect pós-login, e sempre validado contra os vínculos do `/me/contexto` antes de
  valer. Ele **ganha do atalho da Plataforma** (a `/plataforma` o esquece ao abrir), o que muda a
  ordem que a `frontend/04` fixou. Só se lembra `orgId` que o backend deixou abrir, então um que
  respondeu 403 nunca vira destino. Ver `Como ficou` da `frontend/05`.
- **Não há route group por persona** (`(admin)`/`(parceiro)`/`(colaborador)`), e é decisão:
  route group é estático, persona é runtime (vem do `/eu`). O seam por persona mora no
  `AppShell` e no `buildNav`. Ver `Como ficou` da `frontend/04`.
- **Label e path de módulo moram no frontend** (`features/context/modules.ts`), não no contexto:
  o `/eu` devolve só as **chaves** habilitadas, e o `ModuleNav` do descritor só sai pelo
  `GET /modulos`, que é de `platform_admin`. Ligar o flag ainda faz o item aparecer sem deploy —
  quem decide visibilidade é o entitlement. Mexeu no descritor do backend, mexe no catálogo.
- `docker-compose.yml` + `nginx/` — stack completa (Postgres, backend, frontend, nginx).
- Nenhum app de negócio existe ainda — `refeicoes` e `frota` são chave registrada no backend e
  rota-placeholder no frontend, nada mais. Não assuma — confirme lendo o diretório.

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
  declara uma **porta** e o módulo **registra a implementação** em `mount_routes`. São **cinco**
  casos, todos de kernel: `UserReader` (`core/security/identity.py`) ↔
  `set_user_reader_factory(SqlAlchemyUserReader)`; `UserDirectory` (mesmo arquivo) ↔
  `set_user_directory_factory(SqlAlchemyUserDirectory)`; `OrganizationReader`
  (`core/tenancy/context.py`) ↔ `set_organization_reader_factory(SqlAlchemyOrganizationReader)`;
  `PermissionReader` (`core/authz/context.py`) ↔
  `set_permission_reader_factory(SqlAlchemyMembershipReader)`; e `ModuleEntitlementReader`
  (`core/modules/entitlements.py`) ↔
  `set_module_entitlement_reader_factory(SqlAlchemyModuleEntitlementReader)`.
  Ganhar linha extra no `mount_routes` é **privilégio de kernel** — app de negócio consome
  `CurrentUserDep`/`CurrentOrganizationDep`/`require_permission(...)`/`require_module(...)` e
  pronto, sem tocar `core`; plugar é `mount_module(api, <descritor>)`, uma linha.
  **`UserReader` lê identidade, `UserDirectory` a cria** — é o par que deixa o onboarding do
  `access` (`backend/06`) dar login a um convidado sem importar `auth`. E as duas pontas
  recebem a **mesma `SessionDep`** de quem chama: é isso, e não um `try`, que faz o
  auto-cadastro de Parceiro ser atômico entre `users` (do `auth`) e `organizations` (do
  `access`).
  A porta de **e-mail** (`core/notifications/`) é a exceção que confirma a regra: não ganha
  linha no `mount_routes` porque e-mail é infra, não tabela de módulo — o default é um
  `LoggingEmailSender`.
- **Autorização entra por capability, não por papel.** Rota e guard nomeiam a permissão
  (`require_permission("agreements.write")`); quem decide qual papel a tem é
  `PERMISSIONS_BY_ROLE`, no `access`. O `core` não conhece papel nenhum, e `Permission` é `str`
  de propósito: o kernel declara as permissões da plataforma, e cada módulo de negócio declara
  as suas no descritor — **que hoje não liga em nada**, ver o furo conhecido acima.
  Papel/tenant **nunca** entram no token de sessão — mudam a cada request.
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
| `python -m src.modules.access.cli grant --email … --role … [--org …]` | vincula usuário a organização (bootstrap; sem `--org`, a `platform`) |

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
