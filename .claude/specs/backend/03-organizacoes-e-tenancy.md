# 03 — Organizações e tenancy

**Estado:** ✅ implementada (2026-07-16). Subiu com o guard de vínculo permissivo; **o critério
2 fechou com a `backend/04`** (2026-07-16), que trocou o corpo do `SqlAlchemyOrganizationReader`
como previsto. Ver `Como ficou` no fim.
**Depende de:** `backend/01-fundacao.md`, `backend/02-identidade-e-sessao.md`.
**Entrega:** o módulo `access` começa aqui — `organizations` (plataforma/empresa/parceiro),
o convênio Empresa↔Parceiro, e o **contexto de tenant** que escopa todo dado do sistema por
organização.

## Objetivo

Dar ao sistema seu eixo multi-tenant. Toda informação de negócio pertence a uma organização,
e requisições carregam qual organização está ativa. É o que a Central deliberadamente **não**
tem — aqui é o coração.

`access` é o segundo módulo do kernel. Módulos de negócio consomem `current_organization`
(exposto via `core`), nunca importam `access`.

## Fora de escopo

- Membros, papéis e permissões (spec 04) — esta spec entrega organizações e o escopo de
  tenant; *quem* pode agir numa organização é da 04.
- Termos comerciais do convênio (catálogo, preços, subsídio) — esses moram nos módulos de
  negócio (Refeições), pendurados no `partner_agreement`, não aqui.

## Modelo

`organizations`

| coluna | tipo | nota |
|---|---|---|
| `id` | UUID (PK) | |
| `type` | enum `platform` / `company` / `partner` | definido na criação, **imutável** |
| `name` | text | |
| `document` | text, nullable | CNPJ, quando houver |
| `status` | enum `active`/`disabled` | |
| `created_at` | timestamptz | |

- **`platform`** — exatamente uma linha: a Widelab como operadora. Sede dos `platform_admin`.
- **`company`** — os tenants (Empresas). A Widelab-como-cliente é uma linha `company`,
  distinta da linha `platform`.
- **`partner`** — os Parceiros (restaurantes), organização de primeiro nível.

`partner_agreements` — o convênio Empresa↔Parceiro

| coluna | tipo | nota |
|---|---|---|
| `id` | UUID (PK) | |
| `company_id` | UUID → `organizations` (type=company) | |
| `partner_id` | UUID → `organizations` (type=partner) | |
| `status` | enum `active`/`suspended` | |
| `created_at` | timestamptz | |

Único por par `(company_id, partner_id)`. Um Parceiro tem N convênios (atende N Empresas);
cada convênio é o ponto onde os módulos de negócio penduram termos *por Empresa* — preços
diferentes por Empresa, como o protótipo promete.

**Integridade de tipo — os lados do convênio são do tipo certo, e o tipo não muda debaixo
dele.** `type` é imutável (ver tabela `organizations`), e o convênio não confia só na FK
simples pra `organizations(id)`, que aceitaria qualquer org. Enforce estrutural: `UNIQUE
(id, type)` em `organizations` + FKs compostas `(company_id → company)` e `(partner_id →
partner)` contra `organizations(id, type)`. Assim, inserir um `partner_id` que não é
`partner` é **impossível**, e mudar o `type` de uma organização referenciada por um convênio
é bloqueado pelo banco — não é regra que vive só na aplicação. Sem tabela separada por tipo:
seria overengineering enquanto uma organização não precisar ser Empresa **e** Parceiro ao
mesmo tempo (aí o certo seria *papéis de organização*, não `type` — e é migração deliberada,
não corrupção silenciosa).

## Contexto de tenant

A organização ativa viaja no **path**: toda rota escopada por tenant mora sob
`/api/organizacoes/{orgId}/...`. Uma dependency `current_organization` (em `access`, exposta
via `core`):

1. lê o path param `orgId`;
2. valida que o `current_user` tem vínculo (spec 04) naquela organização — senão **403**;
3. devolve a organização.

Tenant no path, não em header nem sessão: a requisição é autoexplicativa, não existe
"organização default" implícita a adivinhar, e a URL do frontend é compartilhável por
organização (ver `frontend/05-selecao-de-organizacao.md`). O mesmo login atende N
organizações — trocar de contexto é navegar pra outro `orgId`. `platform_admin` acessa
qualquer `orgId` (checagem afrouxada pra plataforma).

**Escopo por linha, banco e schema compartilhados.** Toda tabela de negócio carrega
`organization_id` e é filtrada por `current_organization`. É o multi-tenant pragmático do
monólito modular; o `organization_id` viaja junto se um módulo for extraído (o *seam* da
`00-visao-geral.md`). `core` ganha um helper de repositório tenant-scoped pra ninguém
esquecer o filtro.

## Endpoints

Globais (plataforma):

| Método | Rota | Quem | Ação |
|---|---|---|---|
| `POST` | `/api/organizacoes` | `platform_admin` | cria Empresa ou Parceiro (provisiona tenant) |
| `GET` | `/api/organizacoes` | `platform_admin` | lista tenants |
| `GET` | `/api/organizacoes/{orgId}` | membro da org ou `platform_admin` | detalhe |

Escopadas na Empresa (sob `/api/organizacoes/{orgId}`):

| Método | Rota | Quem | Ação |
|---|---|---|---|
| `POST` | `/api/organizacoes/{orgId}/convenios` | `company_admin` | vincula um Parceiro à Empresa `{orgId}` |
| `GET` | `/api/organizacoes/{orgId}/convenios` | membro da Empresa/Parceiro | lista convênios |
| `PATCH` | `/api/organizacoes/{orgId}/convenios/{id}` | `company_admin` | suspende/reativa |

(Os papéis citados são definidos na spec 04; esta spec pode subir com o guard ainda
permissivo e apertar quando a 04 entrar.)

## Critérios de aceite

1. Criar uma organização de cada tipo funciona; existe exatamente uma `platform`.
2. Requisição a `/api/organizacoes/{orgId}/...` de uma organização em que o usuário não tem
   vínculo responde 403.
3. Um convênio é único por `(company_id, partner_id)`; criar duplicado falha.
4. Criar convênio com um `partner_id` que não é `partner` (ou `company_id` que não é
   `company`) falha no banco; mudar o `type` de uma organização referenciada por convênio
   falha. `type` nunca é atualizado pela aplicação.
5. Um repositório tenant-scoped nunca retorna linha de outra organização, mesmo se o
   `organization_id` for omitido no código de negócio (o helper impõe o filtro).
6. Nenhuma tabela de negócio existe sem `organization_id`.

## Como ficou

Os critérios 1, 3, 4 e 5 batem e foram observados rodando contra o Postgres de verdade. O
**critério 2 ficou em aberto por dependência e fechou na spec 04**, e o 6 é vacuamente
verdadeiro hoje — detalhe abaixo.

> **Fechado na `backend/04` (2026-07-16).** O `SqlAlchemyOrganizationReader` agora confere
> `memberships` e afrouxa pra `platform_admin`, como este texto previa. Custou o que a spec
> dizia que custaria: o corpo de um método, mais uma consulta — nenhuma rota, use case ou linha
> do `core` mudou junto. Verificado rodando: um usuário vinculado só a um Parceiro leva **403**
> na Empresa alheia (e vice-versa), e o `platform_admin` alcança qualquer `orgId`. O parágrafo
> abaixo fica como o registro da decisão de subir permissivo — não some.

- **O critério 2 não fecha nesta spec, e isso é estrutural, não esquecimento.** O critério
  cobra 403 pra organização "em que o usuário não tem vínculo", mas vínculo é `memberships`,
  tabela da **spec 04** — que esta spec lista em `Fora de escopo`. Não havia como conferir
  vínculo sem construir a 04 junto. O texto já previa a saída ("esta spec pode subir com o
  guard ainda permissivo"), então: `current_organization` existe, é real e está ligado em
  **todas** as rotas escopadas; o que está permissivo é só o `SqlAlchemyOrganizationReader`,
  que hoje aceita qualquer organização **ativa** pra qualquer usuário **autenticado**.
  Verificado rodando: 401 sem sessão, e **403 de verdade** quando o reader nega — provado
  desativando uma organização (`status='disabled'` → 403 no detalhe e nos convênios). Apertar
  na 04 é trocar o corpo de um método; nenhuma rota, use case ou linha do `core` muda junto.
- **`OrganizationType` mora no `core`, não no `access`.** A spec diz "dependency
  `current_organization` (em `access`, exposta via `core`)", mas `CurrentOrganization` carrega
  o `type`, e um módulo de negócio precisa saber se está numa Empresa ou num Parceiro sem
  importar `access`. Duplicar o enum nos dois lados seria pior. Então o `core` é dono do
  **vocabulário** do contrato (`core/tenancy/`), e o `access` segue dono da **tabela** — a
  seta continua apontando pra dentro, porque quem importa `core` é o módulo.
- **`current_organization` chegou pelo mesmo padrão do `UserReader` da spec 02:** o `core`
  declara a porta `OrganizationReader`, o `access` registra a implementação em `mount_routes`
  (`set_organization_reader_factory`). O `access` é o **segundo** módulo com duas linhas no
  `mount_routes` — privilégio de kernel, como a spec 02 registrou.
- **O helper tenant-scoped virou duas peças, não uma.** A spec pedia "um helper de
  repositório"; o real tem `core/database/tenant.py` (`TenantScopedBase`, dono da coluna
  `organization_id`) além de `repositories/tenant_scoped.py`. Sem a base, o repositório
  genérico não teria como exigir, em tipo, que o model tem `organization_id` — e o escopo
  viraria disciplina em vez de estrutura.
- **Um bug real que só apareceu rodando:** `TenantScopedRepository.get_by_id_or_none` vazava
  linha de outro tenant. O repositório base resolve esse método com `session.get()` direto,
  **sem** passar pelo `_get_model_or_none` que eu havia escopado. Escopar só o helper não
  bastava; o método precisou de override próprio. É exatamente o furo que o critério 5
  existe pra pegar, e ele só apareceu porque o critério foi exercitado de verdade.
- **`POST /convenios` duplicado devolvia 500, não 409.** O `flush()` do repositório já manda o
  `INSERT`, então a constraint estoura **antes** do `commit` — e o `SQLAlchemyUnitOfWork` só
  traduz `IntegrityError` → `ConflictError` no `commit`. A tradução foi pro `create` do
  `PartnerAgreementRepository`. **O mesmo furo existe no `auth`** (e-mail duplicado no
  `UserRepository.create` também viraria 500); não foi corrigido aqui porque mudar o
  comportamento do `auth` é escopo da spec dele, mas fica registrado.
- **A organização `platform` é semeada na migration**, com id fixo
  (`01890000-0000-7000-8000-000000000001`). A spec exige "exatamente uma `platform`" mas
  nenhuma rota a cria (`POST /api/organizacoes` só faz Empresa e Parceiro, e o schema recusa
  `platform` com 422). Sem semear, o "exatamente uma" seria "no máximo uma, e zero na
  prática" — e o bootstrap do primeiro `platform_admin` (specs 02/04) não teria alvo. O "no
  máximo uma" quem garante é um índice único **parcial** (`WHERE type = 'platform'`).
- **Critério 6 é vacuamente verdadeiro**: não existe tabela de negócio ainda — `organizations`
  e `partner_agreements` são kernel, e o convênio é escopado por `company_id`/`partner_id`,
  não por `organization_id`. O que a spec entrega é a **impossibilidade** de esquecer:
  herdar de `TenantScopedBase` é o que dá acesso ao repositório tenant-scoped. O critério só
  passa a ter mordida quando o primeiro app de negócio chegar (fase 2).
- **Sem testes automatizados** — o backend não tem framework de teste, e esta spec não cita
  testes. A verificação foi por `curl` e `psql` contra o Postgres real, mais um script
  temporário pro critério 5, apagado depois. **É dívida**: o furo do `get_by_id_or_none` não
  tem hoje nenhuma rede que impeça a volta. Uma spec de infra de teste (`pytest` +
  Postgres efêmero) é o próximo candidato óbvio.
- **`PATCH /convenios/{id}` de convênio de outra Empresa responde 404, não 403** — quem não
  pode ver o convênio também não deveria descobrir que ele existe.
