# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Superapp Widelab (`apps/administrativo`)

Plataforma web **multi-tenant** que hospeda vários serviços internos ("apps") sob um mesmo
núcleo de identidade, organizações e permissões. Nasce pra resolver dores internas da Widelab
(controle de refeições e de uso da frota) e é construída pra ser **vendida** a outras
empresas. Backend FastAPI + frontend Next, monólito modular.

## A fonte da verdade é `.claude/specs/`, não este arquivo

Antes de implementar qualquer coisa não trivial, leia `.claude/specs/00-visao-geral.md`
inteiro e a spec numerada relevante. As specs registram não só o _quê_, mas o **porquê**, o
que foi decidido **não** fazer ainda, e critérios de aceite explícitos. Este `CLAUDE.md` é um
mapa de navegação rápida — quando ele e uma spec discordarem, **a spec vence**.

**Uma spec é uma pasta com dois arquivos, sempre os mesmos:**

```
.claude/specs/<backend|frontend>/NN-nome-curto/
  spec.md          a decisão: escrita antes, congelada depois
  como-ficou.md    o que aconteceu: nasce na implementação e cresce
```

`spec.md` **não é reescrito** pra bater com o código — se fosse, sumiria a prova do que se
pensava antes de implementar. A divergência entre os dois é o aprendizado, e mora no
`como-ficou.md`. Spec ainda não implementada tem só o `spec.md`, e anexo (diagrama, SQL) mora
na pasta dela.

Na raiz de `.claude/specs/` ficam os artefatos que **atravessam** specs: a `00-visao-geral.md` e
o `banco-de-dados.puml` — um ER do schema do **kernel** (`users`, `organizations`, `memberships`,
`partner_agreements`, `module_entitlements`, `invitations`), que por isso não é de spec nenhuma.
Ele **não** tem as tabelas da frota (migration `0006`); quem mexer nele que as acrescente.

**Este arquivo não guarda estado, e cada camada tem um dono só.** Não replique aqui o que já
tem casa embaixo; um fato em dois lugares vira um fato errado em um deles.

| Pergunta | Onde responde |
| --- | --- |
| Por que isto é assim? O que ficou de dívida? | o `como-ficou.md` da spec |
| Em que pé está cada spec, e o que a bloqueia | `00-visao-geral.md` § `Índice de specs` |
| O que falta fazer, e por que nesta ordem | `00-visao-geral.md` § `Fases` |
| Onde mora o código, e o que não se negocia | aqui |

As três primeiras respostas moram **no repo**, de propósito: um clone novo tem tudo. Memória de
sessão pode indexar isso pra ir mais rápido, mas não é dona de nada — se a memória e o repo
discordarem, o repo vence.

| #   | Backend                           |     | Frontend                   |     |
| --- | --------------------------------- | --- | -------------------------- | --- |
| 01  | fundação (FastAPI hexagonal)      | ✅  | fundação (Next App Router) | ✅  |
| 02  | identidade e sessão (`auth`)      | ✅  | design system              | ✅  |
| 03  | organizações e tenancy (`access`) | ✅  | login e sessão             | ✅  |
| 04  | membros e autorização (`access`)  | ✅  | casca e personas           | ✅  |
| 05  | módulos e entitlements (`access`) | ✅  | seleção de organização     | ✅  |
| 06  | convites e onboarding (`access`)  | ✅  | onboarding                 | ✅  |
| 07  | testes automatizados              | ✅  | telas da frota             | ✅  |
| 08  | gestão de convites (`access`)     | ✅  | gestão da organização      | ✅  |
| 09  | capabilities de módulo            | ✅  | console da Plataforma      | 📋  |
| 10  | **frota** (1º app de negócio)     | ✅  | —                          |     |

📋 = spec escrita, não implementada. **O estado por spec — o que cada uma entregou, o que deixou
de dívida e o que bloqueia a seguinte — está no `Índice de specs` da `00-visao-geral.md`**, que é
mantido junto com as specs. Não confie em contagem de teste ou de rota citada de cabeça: confirme
no repo.

**Use a skill `nova-spec`** pra propor uma spec nova e **`implementar-spec`** pra executar
uma existente — ambas seguem o formato da casa (`Depende de` / `Entrega` / `Objetivo` /
`Fora de escopo` / `Critérios de aceite`).

## Mapa do repositório

Onde as coisas moram. O **porquê** de cada decisão está no `como-ficou.md` da spec apontada — se
a pergunta é "por que assim?", a resposta não está nesta seção.

| Caminho | O que tem | Spec |
| --- | --- | --- |
| `backend/src/core/` | config, database, security, tenancy, authz, modules, notifications, exceptions, logging, pagination, types | `backend/01`, `05` |
| `backend/src/modules/auth/` | identidade e sessão: login, logout, `GET /api/me`, `PUT /api/me/password`, CLI de bootstrap. Migration `0001_users` | `backend/02` |
| `backend/src/modules/access/` | o kernel de autorização: `organizations`, `partner_agreements`, `memberships`, `module_entitlements`, `invitations`. Migrations `0002`–`0005` | `backend/03`–`06`, `08`, `09` |
| `backend/src/modules/frota/` | 1º app de negócio: `vehicles`, `drivers`, `vehicle_usages`. Migration `0006`. 14 rotas e 7 capabilities namespaced (`frota.*`), importando **só** `src.core` | `backend/10` |
| `backend/tests/` | `unit/` (regra pura, roda sem Docker) e `integration/` (Postgres efêmero via testcontainers) | `backend/07` |
| `frontend/src/features/` | `auth`, `context` (casca, nav, guards, seletor de org), `onboarding`, `frota`, `organization` | `frontend/03`–`08` |
| `frontend/src/styles.css` | a paleta — **o único lugar do repo com hex**. Vitrine viva dos primitivos em `/design-system` | `frontend/02` |
| `docker-compose.yml`, `nginx/` | stack completa (Postgres, backend, frontend, nginx) | `backend/01` |

**Rotas do backend.** `POST /api/auth/login` e `/api/auth/logout`; `/api/me`, `/api/me/password`,
`/api/me/contexto`; `/api/organizacoes` (`POST`/`GET`) e `/{orgId}`; e sob
`/api/organizacoes/{orgId}/`: `me`, `membros`, `convenios`, `modulos[/{chave}]`,
`convites[/{id}]` e `frota/*`. **Públicas:** `GET /api/convites/{token}`,
`POST /api/convites/{token}/aceitar`, `POST /api/parceiros/cadastro`.

As migrations ficam em `backend/migrations/versions/` — **fora de `src/`**. A `0002` **semeia a
organização `platform`** (`01890000-0000-7000-8000-000000000001`), valor de que os testes
dependem.

**Rotas do frontend.** `/` **roteia** pra home da persona (não é tela); `(publico)/entrar`,
`(publico)/convites/[token]`, `(publico)/parceiros/cadastro`; `/plataforma` (cross-tenant); e
`/organizacoes/[orgId]/*`, cujo `layout` resolve a persona e monta a casca — com `pessoas`,
`parceiros` e as quatro telas da `frota` dentro.

**`refeicoes` ainda não existe** — é uma chave registrada em `src/api/modules.py` com `grants={}`
e uma rota-placeholder atrás do `ModuleGuard`, nada mais. Não assuma: confirme lendo o diretório.

## Arquitetura (o retrato grande, que exige ler várias specs)

- **Monólito modular multi-tenant.** Um backend, um frontend, um Postgres. A unidade de
  deploy é o container, não o módulo. _Seams_ de extração desenhados, não usados
  (`00-visao-geral.md`).
- **Kernel da plataforma = dois módulos:** `auth` (identidade/sessão) e `access` (organizações,
  membros, autorização, entitlements, onboarding). Os **apps de negócio** (`refeicoes`,
  `frota`) plugam depois e dependem **só** de `core` + dos _contracts_ públicos do kernel —
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
  Plataforma) resolvidas de `GET /api/organizacoes/{orgId}/me`; navegação derivada dos
  módulos habilitados. **Trocar de organização é navegar pra outro `orgId`** — não há store de
  "org ativa", e o seletor só navega.

## Convenções que não se negociam

- **Backend hexagonal:** `src/core` intocável por módulos; `modules/<mod>/` em camadas
  (`domain` → `application` → `adapters`); `application` recebe repositório via `Depends`,
  nunca importa `adapters`; **módulo não importa módulo**; adicionar módulo é uma linha em
  `mount_routes`, sem tocar `core`.
- **`core` nunca importa módulo — a seta aponta pra dentro.** Quando o `core` precisa de algo
  que um módulo é dono (ex.: `current_user` precisa ler `users`, tabela do `auth`), o `core`
  declara uma **porta** e o módulo **registra a implementação** em `mount_routes`. São **cinco**
  casos, todos de kernel:

  | Porta | Registro em `mount_routes` |
  | --- | --- |
  | `UserReader` (`core/security/identity.py`) | `set_user_reader_factory(SqlAlchemyUserReader)` |
  | `UserDirectory` (mesmo arquivo) | `set_user_directory_factory(SqlAlchemyUserDirectory)` |
  | `OrganizationReader` (`core/tenancy/context.py`) | `set_organization_reader_factory(SqlAlchemyOrganizationReader)` |
  | `PermissionReader` (`core/authz/context.py`) | `set_permission_reader_factory(SqlAlchemyMembershipReader)` |
  | `ModuleEntitlementReader` (`core/modules/entitlements.py`) | `set_module_entitlement_reader_factory(SqlAlchemyModuleEntitlementReader)` |

  Ganhar linha extra no `mount_routes` é **privilégio de kernel** — app de negócio consome
  `CurrentUserDep`/`CurrentOrganizationDep`/`require_permission(...)`/`require_module(...)` e
  pronto, sem tocar `core`; plugar é `mount_module(api, <descritor>)`, uma linha. A porta de
  e-mail (`core/notifications/`) é a exceção que confirma a regra: não ganha linha porque e-mail
  é infra, não tabela de módulo — o default é um `LoggingEmailSender`, então em dev o convite
  sai no log, não na caixa de entrada. Ver `backend/06` e `backend/09`.
- **Autorização entra por capability, não por papel.** Rota e guard nomeiam a permissão
  (`require_permission("agreements.write")`); quem decide qual papel a tem é
  `PERMISSIONS_BY_ROLE`, no `access`. O `core` não conhece papel nenhum, e `Permission` é `str`
  de propósito: o kernel declara as permissões da plataforma, e cada módulo declara as suas no
  `grants` do descritor, que o `PermissionReader` soma ao mapa do kernel (`backend/09`).
  Papel/tenant **nunca** entram no token de sessão — mudam a cada request.
- **Teste não é opcional no backend.** Todo critério de aceite que se observa por requisição ou
  por SQL vem com teste em `backend/tests/` **na mesma entrega**, não em spec futura. Fechar sem
  teste é exceção justificada no `Como ficou`. A suíte fala com **Postgres de verdade**
  (testcontainers, porta efêmera): as invariantes deste backend moram no banco, e mock ou SQLite
  ficariam verdes testando nada. **`src.main` nunca é importado no topo de um módulo de teste** —
  ele lê `get_config()` no import e congelaria a config antes de o harness apontar pro container.
  Ver `backend/07-testes/spec.md`.
- **Schema só via Alembic**, sem `create_all`. Nomes de tabela `snake_case` no plural, **sem**
  prefixo `T0xx`. E-mail é `CITEXT`; senha é **Argon2id**, nunca bcrypt. Model de módulo novo
  entra em `migrations/env.py`, senão o `--autogenerate` propõe dropar as tabelas dele. **FK que
  cruza módulo vive só na migration** (`memberships.user_id`, `module_entitlements.granted_by`,
  as três `fk_*_organization` da frota) — declará-la no model faria módulo importar módulo. Como
  consequência o **`alembic check` não é verde e não será**: ele propõe dropar essas seis. Recuse.
- **Mexeu no mapa, mexe na migration.** `ROLES_BY_ORGANIZATION_TYPE` (em
  `access/domain/permissions.py`) é espelhado por um `CHECK` **gerado** em `memberships` — o banco
  é quem garante que papel só vale no tipo de organização certo. Mesma disciplina do outro lado:
  **mexeu no descritor de módulo do backend, mexe no catálogo do frontend**, porque label e path
  de módulo moram lá (`features/<mod>/module.ts`), não no `/me`.
- **Instante que entra na API exige fuso.** `AwareDatetime` nos schemas e nas query params de
  período; um instante sem fuso é 422 e o servidor **não** normaliza, porque não sabe onde o dado
  foi digitado. Quem carimba o offset é o frontend (`features/frota/lib/instants.ts`) — a string
  crua de um `<input datetime-local>` nunca vai pra API. Foi um 500 e um filtro que errava calado;
  ver `backend/10` e o `Como ficou` da `frontend/07`.
- **Rotas em português; tenant no path.** `/api/me*` é o usuário global; `/api/organizacoes/{orgId}/me`
  é "eu nesta organização". Nomes de tabela, coluna e valores de enum seguem em **inglês**.
- **Organização tem um tipo só** (`platform`/`company`/`partner`), definido na criação e
  **imutável**; a integridade dos lados do convênio é garantida no banco (FK composta), ver
  `backend/03`.
- **Sessão:** JWT assinado pela app (HS256) em cookie httpOnly; **sem papel ou organização no
  token** — isso muda por request e é resolvido pelo `access`.
- **Frontend:** TypeScript strict; **TanStack Query** com fetch client-side; **zod** com tipos
  sempre `z.infer` (nunca à mão); shadcn/Radix; estrutura por `features/<domínio>`; alias
  `#/*` → `./src/*`; componente de domínio mora em `features/<domínio>/components`, nunca solto.
  **Módulo não edita a casca pra caber** — navegação interna é problema do módulo (a frota tem
  quatro telas e um item de menu, com abas dentro).
- **Cor só por token.** O hex mora **só** no bloco de paleta de `frontend/src/styles.css`
  (`--palette-*`), mapeado pras utilidades por `@theme inline`. Tela nenhuma usa hex solto nem
  cor do Tailwind (`bg-slate-900`) — use as utilidades de token (`bg-surface`, `text-muted`,
  `ring-ring`). Ver `frontend/02-design-system/spec.md`.

## Comandos

Definidos em `backend/01-fundacao/spec.md` e `frontend/01-fundacao/spec.md`; o scaffold existe, então
eles valem. `docker compose up db` sobe só o Postgres (backend/frontend rodam nativos em dev);
`docker compose up` sobe a stack inteira atrás do nginx.

| Backend (de `backend/`, via `uv run`)                                 |                                                                      |
| --------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `uvicorn src.main:app --reload`                                       | sobe em dev (`:8000`)                                                |
| `ruff format .` / `ruff check .` / `mypy src tests`                   | formata / lint / typecheck (o typecheck cobre a suíte também)        |
| `pytest`                                                              | a suíte (**exige Docker rodando**)                                   |
| `pytest tests/unit`                                                   | só a regra pura, sem Docker                                          |
| `pytest -k entitlement`                                               | um recorte                                                           |
| `alembic revision --autogenerate -m "msg"` / `alembic upgrade head`   | migration                                                            |
| `python -m src.modules.auth.cli create-user --email … --name …`       | cria usuário (bootstrap)                                             |
| `python -m src.modules.access.cli grant --email … --role … [--org …]` | vincula usuário a organização (bootstrap; sem `--org`, a `platform`) |

| Frontend (de `frontend/`, via `npm`)      |                                                   |
| ----------------------------------------- | ------------------------------------------------- |
| `run dev`                                 | sobe em dev (`:3000`, rewrite `/api/*` → backend) |
| `run typecheck` / `run lint` / `run test` | tsc / ESLint / Vitest                             |
| `run build`                               | build de produção                                 |

## Skills deste projeto

- **`nova-spec`** — escreve uma spec nova em `.claude/specs/` no formato da casa.
- **`implementar-spec`** — implementa uma spec existente e confere cada critério de aceite.
- **`run`** — sobe a stack nesta máquina (compose, ou backend/frontend nativos). Embute as
  armadilhas do ambiente do Kauan que não estão no repo: o Postgres do compose é `internal`
  (`localhost:5432` é de outro projeto — precisa do forwarder `socat`), `pkill` não mata no
  Windows (`taskkill /F /PID`), e `uv` que baixa pacote precisa de `NO_PROXY='*'`.
- **`verify`** — lint/typecheck/testes das duas pontas. Deixa claro que `pytest` exige Docker e
  ignora o `DATABASE_URL` do shell. **`npm run check` é verde desde 2026-07-22** (o
  `.gitattributes` e o `endOfLine: auto` mataram a dívida de CRLF), então vermelho ali é erro
  seu.

## Relação com a Central de Aplicações (`apps/central`)

O superapp herda as **convenções** da Central (hexagonal, Postgres async, feature-based, specs
no formato da casa) mas rejeita a **topologia** dela (federação por subdomínio, `autentica não
autoriza`) — situações opostas, ver `00-visao-geral.md`. No futuro, o superapp vira **consumidor
do SSO da Central** via a porta de autenticação (`backend/02`), sem reescrever autorização.
