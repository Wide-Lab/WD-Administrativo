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
| 10  | **frota** (1º app de negócio)     | ✅  | —¹                         |     |

📋 = **spec escrita, não implementada**. Sobrou **uma**: a `frontend/09`, o console da Plataforma
— a que destrava vender. As `07` e `08` foram implementadas em 2026-07-21, em duas worktrees em
paralelo, e o merge custou **um** conflito (`components/ui/table.tsx`, criado pelas duas).
**A `09` está bloqueada** por uma spec de backend ainda não escrita: o e-mail do primeiro admin no
`POST /organizacoes` (decidido em 2026-07-21) — sem ela o console provisiona Empresa em que
ninguém entra.

¹ **a dívida em aberto do frontend, e ela foi adiada de propósito — agora com a conta maior.**
Não há testing-library/jsdom: `nav`, `home-path`, os rótulos de erro, a política de senha, os
schemas zod, as traduções de erro e os filtros de URL têm teste puro (**180**, `npm run test`),
mas casca, guards, `Can`, seletor, os dois formulários de onboarding e agora **as seis telas das
`07`/`08`** foram verificados só a olho — e as `07`/`08` **nem isso**: foram implementadas sem
subir a stack, contra os contratos lidos no código do backend, e checadas por `build`. Junto com a
**CI** (que a `backend/07` deixou encaminhada e que precisa da allowlist do `alembic check`),
ficou **para depois das telas** — decisão do Kauan em 2026-07-20. Em troca, cada spec de tela
obriga **teste do que é função pura na própria entrega** (schemas zod, tradução de erro, filtros
de URL, `buildNav`), e foi o que segurou 112 dos 180. Quem escrever a spec de teste de componente
começa pelo formulário de viagem da `frontend/07`.

**Use a skill `nova-spec`** pra propor uma spec nova e **`implementar-spec`** pra executar
uma existente — ambas seguem o formato da casa (`Depende de` / `Entrega` / `Objetivo` /
`Fora de escopo` / `Critérios de aceite`).

## Estado atual — o backend está duas fases à frente do frontend, e é isso que falta

Backend `01`–`07` e frontend `01`–`06` estão implementados: dá pra subir a stack, logar,
provisionar Empresas/Parceiros, conveniá-los, vincular pessoas com papel, **vender módulo
ligando um flag** — e **o backend nega de verdade** (403 em tenant sem vínculo, 403 em permissão
faltante, 403 em módulo não contratado). Com a `frontend/04`, logar já cai na casca da sua
persona, com a navegação saindo dos módulos que o **tenant** contratou; com a `frontend/05`, quem
tem mais de um vínculo **troca de organização pelo seletor do masthead**, e o pós-login volta pra
última organização visitada. Com a `backend/06` + `frontend/06`, **entrar no sistema deixou de
ser CLI e ganhou tela**: Colaborador é convidado e aceita por token em `/convites/[token]`;
Parceiro se auto-cadastra em `/parceiros/cadastro`. Com a `backend/07`, **a dívida de teste do
backend foi paga**: 69 testes em ~13s contra Postgres de verdade prendem o que as `02`–`06`
registraram como dívida. Com a `backend/09`, **o último bloqueio do primeiro app de negócio caiu**:
uma capability declarada por um módulo chega a um papel — 86 testes. E com a `backend/10`,
**o primeiro app de negócio existe**: a Frota tem schema (migration `0006`), 14 rotas sob
`/api/organizacoes/{orgId}/frota/*` e sete capabilities próprias, importa **só** `src.core`, e
`src/core` não mudou em nenhuma linha. Um `manager` cadastra veículo e lança viagem
porque o `grants` do descritor chega até ele, sem uma linha em `PERMISSIONS_BY_ROLE`. E com a
`backend/08`, **o convite deixou de ser via só de ida**: listar e revogar viraram rota e o
`partner_admin` passou a convidar — 237 testes.

**O desequilíbrio de rota consumida praticamente fechou** (2026-07-21). Com a `frontend/07`, a
frota tem tela: quatro delas — viagens, veículos, condutores e quilometragem — sob a rota que o
`ModuleGuard` já protegia, e o descritor mudou-se do catálogo pra `features/frota/module.ts`. Com
a `frontend/08`, a organização administra a si mesma: Pessoas (membros e convites em abas) e
Parceiros (convênios), com o `buildNav` ganhando um terceiro grupo, o do kernel, decidido por
capability. **O que segue sem interface é o que a `frontend/09` cobre** — `modulos` e o CRUD de
`organizacoes`, que são atos da Plataforma sobre um tenant. CI e teste de componente seguem
adiados, nota ¹, e a conta subiu: seis telas novas sem cobertura de DOM.

**Duas dívidas que a `backend/10` descobriu e não pôde pagar:** `PageResponse`, `get_page_params`
e o helper `_pg_enum` moram no `access`, um app de negócio não pode importá-los, e o critério da
spec proibia promovê-los ao `core` — então a frota tem cópias, e Refeições vai copiar de novo
(promovê-los é spec própria). E o **`alembic check` nunca esteve limpo**: FK que cruza módulo vive
só na migration desde a `0003`, e ele propõe dropar seis delas — a spec de CI vai precisar de
allowlist. Isso contradiz a seção `Sem migration` da `09`, que afirmava o contrário — e que já
está anotada.

**Quatro furos que as telas acharam no backend**, todos por olhar um contrato do lado de quem o
consome: (1) **`PATCH /membros/{id}` não impede auto-rebaixamento nem a perda do último
administrador** — um `company_admin` se rebaixa e a organização fica sem quem a administre;
(2) **uma Empresa recém-provisionada não ganha o primeiro membro por tela nenhuma** —
`platform_admin` não tem `invitations.write` e `POST /membros` não existe; (3) **não há rota pra
uma Empresa descobrir Parceiros**, então criar convênio começa colando um UUID; e (4) — achado ao
**implementar**, em 2026-07-21 — **`MemberResponse` não devolve nome nem e-mail**, e nenhuma das
37 rotas traduz `user_id` em pessoa. A lista de membros mostra UUID, e o e-mail de quem foi
convidado **aparece na aba Convites e some quando a pessoa aceita**. O quarto é o mais forte dos
quatro pela forma como apareceu: as `07` e `08`, rodando **em paralelo e sem contato**, esbarraram
nele pelos dois lados (o select de condutor e as colunas da lista). Nenhum é decidido pelo
frontend. Ver `frontend/07`, `frontend/08` e `frontend/09`.

**Uma dívida menor que a `frontend/07` registrou:** o `core` devolve `code: "conflict"` pros
**cinco** conflitos distintos de `vehicle_usages`, então a tela discrimina a sobreposição de
período **pelo texto da mensagem**. Está contido em `lib/frota-error.ts` e preso por teste com as
strings literais do backend — reescrever a mensagem lá quebra teste aqui. O conserto é `code` por
constraint.

O que existe hoje:

- `backend/` — `src/core` (config, database, security, **tenancy**, **authz**, **modules**,
  **notifications**, exceptions, logging, pagination, types) + `src/modules/auth/` completo:
  login, logout, `GET /api/me`, `PUT /api/me/password`, CLI de bootstrap, migration
  `0001_users`.
- `src/modules/access/` — `organizations` (platform/company/partner), `partner_agreements`
  (convênio), `memberships` (usuário↔org↔papel), `module_entitlements` (Empresa↔módulo) e
  `invitations` (convite↔papel). Rotas: `POST`/`GET /api/organizacoes`,
  `GET /api/organizacoes/{orgId}`, `/convenios` (criar, listar, suspender/reativar),
  `GET /api/me/contexto`, `GET /api/organizacoes/{orgId}/me`,
  `GET`/`PATCH /api/organizacoes/{orgId}/membros`, `GET`/`PUT`/`DELETE
/api/organizacoes/{orgId}/modulos[/{chave}]`, `POST`/`GET /api/organizacoes/{orgId}/convites`,
  `DELETE /api/organizacoes/{orgId}/convites/{id}`, e as
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
  nunca é gravado.
- **Gerir convite é listar e revogar** (`backend/08`, os buracos que a `06` deixou e que já estão
  fechados). `GET .../convites` é `invitations.read` (capability nova) e devolve o status
  **efetivo** — vencido sai como `expired` sem nada ter gravado a coluna —, com `?status=` sobre o
  efetivo e, **sem o parâmetro, só os pendentes**. Filtrar é SQL, não `filter()` em Python: o
  `total` da paginação sai do mesmo `WHERE`, e filtrar depois de paginar faria a lista mentir o
  próprio tamanho. O preço é o `effective_status` existir duas vezes (Python e SQL), preso por um
  teste que compara as duas leituras item a item. `DELETE .../convites/{id}` é `invitations.write`,
  **soft** (grava `revoked`, mantém a linha, que é o que faz o aceite recusar com 410 e não 404) e
  por `id`, nunca por token. 204 no pendente e no já revogado (idempotente), **409 no já aceito**
  (aquele virou membro; tirar acesso é `members.write`), **404 — não 403 — no de outra
  organização**, pra a resposta não virar oráculo. A revogação é `UPDATE ... WHERE id AND
  organization_id AND status = 'pending'`: **a escrita decide e a leitura só explica** o 404/409
  depois, senão a corrida que o `UPDATE` fecha voltaria pela porta dos fundos.
- **Parceiro cresce, e não custou rota nova** (`backend/08`): `partner_admin` ganhou
  `invitations.read`/`invitations.write` e usa as **mesmas** três rotas de convite. Antes disso o
  auto-cadastro criava só o primeiro `partner_admin`, e o segundo membro de um Parceiro só nascia
  pela CLI. `partner_operator` segue sem nenhuma das duas, e `platform_admin` **também não as
  tem** — convidar é ato da organização, não da Plataforma, como o `agreements.write`.
- **Papéis e permissões são fixos e declarados em código**, em `access/domain/permissions.py`
  (`ROLES_BY_ORGANIZATION_TYPE`, `PERMISSIONS_BY_ROLE`, `persona_for`). Papel só vale no tipo
  de organização certo, e **quem garante é o banco**: `memberships` tem um `organization_type`
  ancorado por FK composta contra `organizations(id, type)` + um `CHECK` **gerado** do mapa do
  domínio. Mexeu no mapa, mexe na migration.
- **Entitlement é presença de linha em `module_entitlements`** — não há coluna de ligado, e
  ausência é negação. Só Empresa contrata, e quem garante é o banco (FK composta contra
  `organizations(id, type)`, tipo fixado em coluna gerada). `require_module` (`core/modules/`)
  nega com 403 e **não afrouxa pra `platform_admin`** — diferente de `require_permission`, a
  pergunta é o que o _tenant_ comprou, não quem é o usuário. Só `platform_admin` liga/desliga
  (`modules.read`/`modules.write`).
- **Módulo de negócio pluga com uma linha:** `mount_module(api, <ModuleDescriptor>)` em
  `mount_routes` registra o módulo no `ModuleRegistry` e pendura as rotas sob
  `/api/organizacoes/{orgId}/<chave>/*` já atrás do `require_module` — prefixo e guard não são
  disciplina do módulo. `refeicoes` ainda é só uma **chave registrada** em `src/api/modules.py`,
  com `grants={}` (placeholder até a fase 2). `frota` **já saiu de lá**: o descritor vive em
  `src/modules/frota/module.py`, com router e capabilities de verdade. Na prática a "uma linha"
  são **três pontos de contato** — a linha do `mount_module`, o import dos models em
  `migrations/env.py` e a saída do placeholder —, nenhum deles porta de kernel. Ver `Como ficou`
  da `10`.
- **Capability de módulo chega a papel pelo `grants` do descritor** (`backend/09`, o furo que a
  `05` registrou e que já está fechado). O descritor declara `grants: Mapping[papel,
  frozenset[Permission]]` — não mais uma lista plana —, e `module_permissions_for` soma os
  módulos registrados ao `PERMISSIONS_BY_ROLE` dentro do `SqlAlchemyMembershipReader`. Um app de
  negócio autoriza as próprias rotas com o mesmo `require_permission(...)` do kernel, **sem uma
  linha no `access` e sem tocar `core`**. `permissions` continua existindo como propriedade
  derivada (o catálogo), e `<DESCRITOR>.permission("x.write")` monta a capability com prefixo.
  Duas regras derrubam a **subida**, não o request: capability de módulo é **namespaced** pela
  chave (`register_module`, no `core` — sem isso um módulo se daria `organizations.write`), e
  **módulo não concede a `platform_admin`** nem a papel inexistente (`validate_module_grants()`,
  no fim do `mount_routes`, porque só o `access` conhece `Role`). A Widelab vende módulo; ela não
  opera a frota do cliente. **Dívida:** o `/me` e o guard somam a permissão em dois lugares
  distintos que nada obriga a concordar — ver `Como ficou` da `backend/09`.
- **Criar membro é convite** (`POST /api/organizacoes/{orgId}/convites` + aceite), não `POST`
  direto. A **CLI de vínculo continua**, agora só pro que o convite não alcança — que são **dois
  casos**, não um: o bootstrap do primeiro `platform_admin`, que não tem quem o convide, e **o
  primeiro membro de qualquer organização recém-provisionada**, pelo mesmo motivo (a `frontend/09`
  achou este; `platform_admin` não tem `invitations.write` e `POST /membros` não existe). O
  segundo **já tem saída decidida e não escrita** (Kauan, 2026-07-21): `POST /organizacoes` passa a
  aceitar o e-mail do primeiro admin e cria o convite na mesma transação, como o auto-cadastro de
  Parceiro faz — quando essa spec de backend existir, a CLI volta a ter um caso só. (O
  segundo membro de um Parceiro era um terceiro caso, e deixou de ser: o `partner_admin` convida.)
  `python -m src.modules.access.cli grant --email … --role … [--org …]`; sem `--org`, o
  alvo é a organização `platform`.
- `frontend/` — scaffold Next, design system (tokens em `src/styles.css`, primitivos shadcn,
  vitrine em `/design-system`), feature `auth` (`(publico)/entrar`, `use-session`, guarda de
  rota, `PasswordFields` + a política de senha em `schema.ts`), feature `context`: `use-context`
  (`/api/me/contexto`), `use-org-context` (`/me` + nome da org), `buildNav`/`homePathFor`
  (puras, testadas), `AppShell`, `Can`, `ModuleGuard`, `OrganizationSwitcher` (o seletor do
  masthead), `lib/labels.ts` (rótulos de papel/tipo) e `lib/last-org.ts` (o último `orgId`,
  único uso de `localStorage`) e `lib/roles.ts` (o espelho de `ROLES_BY_ORGANIZATION_TYPE`, que
  não vem do backend porque nenhuma rota o expõe); feature `onboarding`, as duas telas públicas de
  entrada; feature `frota` (`frontend/07`), as quatro telas do primeiro app de negócio; e feature
  `organization` (`frontend/08`), Pessoas e Parceiros.
  Rotas: `/` **roteia** pra home da persona (não é tela), `(publico)/entrar`,
  `(publico)/convites/[token]`, `(publico)/parceiros/cadastro`, `/plataforma`
  (cross-tenant, guarda por vínculo de plataforma) e `/organizacoes/[orgId]/*`, cujo `layout`
  resolve a persona e monta a casca — com `pessoas`, `parceiros` e as quatro da `frota` dentro.
  **`refeicoes` é a única rota-placeholder que sobrou** atrás do `ModuleGuard`; a fase 2 a
  substitui.
- **Onboarding no frontend são duas telas públicas, e nenhuma delas monta a home da persona.**
  O aceite (`/convites/[token]`) e o auto-cadastro (`/parceiros/cadastro`) terminam num
  `router.replace('/')`: o convite público **não devolve `orgId`** (backend/06), e quem sabe pra
  onde ir é a `/`, que lê o `/me/contexto` já com o vínculo novo. Quem define senha usa o
  **`PasswordFields`** (`features/auth/components`) e a `passwordFieldsShape` — uma política, um
  número (`PASSWORD_MIN_LENGTH`). **A resposta do aceite é uniforme** pra conta nova e existente
  (200, mesmo corpo), e é isso, não a tela, que impede vazar quem já é cadastrado; o **409 do
  auto-cadastro conta** que o e-mail existe, e é exceção consciente. Ver `Como ficou` da
  `frontend/06`.
- **A `/parceiros/cadastro` não tem link em tela nenhuma, e a ausência é a decisão** (Kauan,
  2026-07-21) — não é esquecimento pra alguém "consertar" com um "É um parceiro? Cadastre-se" no
  login. Quem manda o link é a Widelab, por fora. Um Parceiro sem convênio é organização órfã
  (convênio é ato da Empresa, `agreements.write`, que nem `platform_admin` tem), e um restaurante
  que se cadastra sozinho não atende ninguém e ainda ocupa o próprio e-mail pro cadastro combinado
  que viria depois. O auto-cadastro é atalho pra quem já foi chamado, não porta de descoberta.
- **A organização ativa é o `orgId` da URL — não há store de "org ativa", e o seletor só navega.**
  O `localStorage` guarda **uma** coisa (`lib/last-org.ts`): o último `orgId` visitado, usado só
  pra decidir o redirect pós-login, e sempre validado contra os vínculos do `/me/contexto` antes de
  valer. Ele **ganha do atalho da Plataforma** (a `/plataforma` o esquece ao abrir), o que muda a
  ordem que a `frontend/04` fixou. Só se lembra `orgId` que o backend deixou abrir, então um que
  respondeu 403 nunca vira destino. Ver `Como ficou` da `frontend/05`.
- **Não há route group por persona** (`(admin)`/`(parceiro)`/`(colaborador)`), e é decisão:
  route group é estático, persona é runtime (vem do `/me`). O seam por persona mora no
  `AppShell` e no `buildNav`. Ver `Como ficou` da `frontend/04`.
- **Label e path de módulo moram no frontend**, não no contexto: o `/me` devolve só as **chaves**
  habilitadas, e o `ModuleNav` do descritor só sai pelo `GET /modulos`, que é de `platform_admin`.
  Ligar o flag ainda faz o item aparecer sem deploy — quem decide visibilidade é o entitlement.
  Mexeu no descritor do backend, mexe no catálogo. **O catálogo agora compõe em vez de declarar**
  (`frontend/07`): a frota traz o seu de `features/frota/module.ts`, como o backend fez com
  `src/api/modules.py`, e `features/context/modules.ts` guarda só `refeicoes` até a fase 2.
- **`buildNav` monta três grupos, não dois** (`frontend/08`): Início, um item por módulo
  contratado, e os do **kernel** — Pessoas (`members.read`) e Parceiros. Ele recebe `permissions`
  desde então. Um módulo **não** edita o menu da casca pra caber: a frota tem quatro telas e um
  item só, com a navegação interna em abas — módulo que precisa mexer no núcleo pra existir quebra
  a promessa de que módulo pluga. Ver `Como ficou` da `frontend/07`.
- `backend/tests/` — `pytest` contra a app de verdade (httpx + `ASGITransport`, sem rede) e um
  Postgres efêmero por sessão (testcontainers, **porta efêmera** — a máquina de dev já tem outro
  projeto em `localhost:5432`). `unit/` é regra pura e roda sem Docker; `integration/` migra com
  `alembic upgrade head` e dá `TRUNCATE` + reseed da org `platform` entre cada teste — `TRUNCATE`
  e não rollback, porque é o que deixa testar a **atomicidade** do auto-cadastro de Parceiro. A
  fixture que decide a ergonomia é `como(role=…, org=…)`: login de verdade, cliente com cookie.
  **237 testes** depois da `backend/08` (216 + 19 de gestão de convite + 2 do fuso da frota).
  Duas fixtures de registry, e a
  diferença importa: `registry_isolado` salva e restaura, `registry_vazio` **também limpa** — quem
  afirma igualdade exata sobre `module_permissions_for(...)` precisa da segunda, porque a frota
  agora concede de verdade e entraria na soma.
  **`src.main` nunca é importado no topo de um módulo de teste** — ele lê `get_config()` no
  import, e isso congelaria a config antes de o harness apontar pro container. Ver `backend/07`.
- `docker-compose.yml` + `nginx/` — stack completa (Postgres, backend, frontend, nginx).
- `src/modules/frota/` — **o primeiro app de negócio** (`backend/10`), em camadas e importando
  **só** `src.core`. `vehicles`, `drivers` e `vehicle_usages` (migration `0006`), todas com FK
  composta contra `organizations(id, type)` — só Empresa tem frota. Rotas: CRUD de veículo e
  condutor (**sem `DELETE`**: desativar é `PATCH status=inactive`, porque o histórico é o
  produto), `GET`/`POST /usos`, `PATCH`/`DELETE /usos/{id}`, `POST /usos/{id}/encerrar` e
  `GET /relatorios/quilometragem`. Sete capabilities namespaced (`frota.vehicles.*`,
  `frota.drivers.*`, `frota.usages.read|write|write_own`), declaradas em
  `frota/domain/permissions.py` e concedidas a `company_admin`, `manager` e `collaborator`.
- **Na frota, lançamento retroativo é o caso normal, e isso desenhou o schema.** `started_at` e
  `ended_at` são **digitados** — não existe rota "iniciar viagem agora", e data futura é 422 da
  aplicação (um `CHECK` com `now()` é impossível no Postgres). A peça central é
  `ex_vehicle_usages_no_overlap`, uma constraint de **exclusão** (`EXCLUDE USING gist`, exige
  `btree_gist`): um veículo não pode ter duas viagens com período sobreposto, e como
  `tstzrange(started_at, NULL)` é sem limite superior, ela entrega de graça "um veículo, uma
  viagem aberta". O range é `[)`, então devolver o carro às 12h e outro pegá-lo às 12h **não**
  colide. Sobreposição é 409 traduzido de `IntegrityError`, nunca um `SELECT` antes.
  **Todo instante que entra exige fuso** (`AwareDatetime` nos schemas e nos `de`/`ate`), e um sem
  fuso é 422 — o servidor não normaliza, porque não sabe onde a viagem foi digitada. O frontend
  carimba o offset em `features/frota/lib/instants.ts`; a string crua do `<input datetime-local>`
  **não** vai pra API. Foi um 500 no lançamento em 2026-07-22, e o filtro de período errava calado
  pelo mesmo motivo — ver o `Como ficou` da `frontend/07`.
- **Condutor é entidade própria, não `membership`** — o motorista terceirizado dirige e nunca
  loga. `drivers.user_id` é o vínculo opcional com quem tem login, e **não tem FK nenhuma, nem na
  migration**: é o primeiro teste do seam de extração, e uma FK daqui pra `users` é o que tornaria
  `frota` não-destacável. Quem tem `frota.usages.write_own` age só sobre o uso cujo `driver_id` é
  o seu; `GET /usos` é a **única rota do módulo sem `require_permission`** — a capability decide o
  *escopo* do que volta, não se a porta abre.
- `refeicoes` segue sem existir — chave registrada no backend e rota-placeholder no frontend,
  nada mais. Não assuma — confirme lendo o diretório.

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
- **Teste não é opcional no backend.** Todo critério de aceite que se observa por requisição ou
  por SQL vem com teste em `backend/tests/` **na mesma entrega**, não em spec futura. Fechar sem
  teste é exceção justificada no `Como ficou` — não o default, como foi nas `03`–`06`. A suíte
  fala com **Postgres de verdade** (testcontainers, porta efêmera) e o schema sai de `alembic
upgrade head`: as invariantes deste backend moram no banco, e mock ou SQLite ficariam verdes
  testando nada. Ver `backend/07-testes.md`.
- **Schema só via Alembic**, sem `create_all`. Nomes de tabela `snake_case` no plural, **sem**
  prefixo `T0xx`. E-mail é `CITEXT`; senha é **Argon2id**, nunca bcrypt. Model de módulo novo
  entra em `migrations/env.py`, senão o `--autogenerate` propõe dropar as tabelas dele. **FK que
  cruza módulo vive só na migration** (`memberships.user_id`, `module_entitlements.granted_by`,
  as três `fk_*_organization` da frota) — declará-la no model faria módulo importar módulo. Como
  consequência o **`alembic check` não é verde e não será**: ele propõe dropar essas seis. Recuse.
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
- **Cor só por token.** O hex mora **só** no bloco de paleta de `frontend/src/styles.css`
  (`--palette-*`), mapeado pras utilidades por `@theme inline`. Tela nenhuma usa hex solto nem
  cor do Tailwind (`bg-slate-900`) — use as utilidades de token (`bg-surface`, `text-muted`,
  `ring-ring`). Ver `frontend/02-design-system.md`.

## Comandos

Definidos em `backend/01-fundacao.md` e `frontend/01-fundacao.md`; o scaffold existe, então
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
  ignora o `DATABASE_URL` do shell, e que **`npm run format`/`check` não devem rodar** (tocam o
  repo inteiro e afogam o diff em CRLF; formate só seus arquivos com `--end-of-line auto`).

## Relação com a Central de Aplicações (`apps/central`)

O superapp herda as **convenções** da Central (hexagonal, Postgres async, feature-based, specs
no formato da casa) mas rejeita a **topologia** dela (federação por subdomínio, `autentica não
autoriza`) — situações opostas, ver `00-visao-geral.md`. No futuro, o superapp vira **consumidor
do SSO da Central** via a porta de autenticação (`backend/02`), sem reescrever autorização.
