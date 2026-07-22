# 03 — Organizações e tenancy

**Estado:** ✅ implementada (2026-07-16). Subiu com o guard de vínculo permissivo; **o critério
2 fechou com a `backend/04`** (2026-07-16), que trocou o corpo do `SqlAlchemyOrganizationReader`
como previsto. Ver [`como-ficou.md`](./como-ficou.md).
**Depende de:** `backend/01-fundacao/spec.md`, `backend/02-identidade-e-sessao/spec.md`.
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
organização (ver `frontend/05-selecao-de-organizacao/spec.md`). O mesmo login atende N
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
