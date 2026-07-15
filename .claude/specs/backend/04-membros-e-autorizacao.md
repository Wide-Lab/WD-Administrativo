# 04 — Membros e autorização

**Depende de:** `backend/02-identidade-e-sessao.md`, `backend/03-organizacoes-e-tenancy.md`.
**Entrega:** `memberships` (usuário↔organização↔papel), o conjunto de papéis por tipo de
organização, o guard de permissão, a resolução de persona, e o endpoint de contexto que
alimenta a casca do frontend.

## Objetivo

Responder "quem é você **nesta** organização e o que pode fazer". Identidade (spec 02) é
global; autorização é sempre *dentro de uma organização*. O mesmo usuário pode ser
`collaborator` numa Empresa e `partner_admin` num Parceiro.

## Fora de escopo

- Entitlement de módulo (spec 05) — o guard de módulo é lá; aqui é papel/permissão.
- Papéis customizados por cliente — o conjunto de papéis é fixo por tipo de organização
  nesta fase; papéis definidos pelo cliente ganham spec própria se um dia forem pedidos.

## Modelo

`memberships`

| coluna | tipo | nota |
|---|---|---|
| `id` | UUID (PK) | |
| `user_id` | UUID → `users` | |
| `organization_id` | UUID → `organizations` | |
| `role` | enum (ver abaixo) | |
| `status` | enum `active`/`disabled` | |
| `created_at` | timestamptz | |

Único por `(user_id, organization_id)` — um papel por pessoa por organização nesta fase.

## Papéis por tipo de organização

| Tipo de org | Papéis |
|---|---|
| `platform` | `platform_admin` |
| `company` | `company_admin`, `hr`, `finance`, `manager`, `collaborator` |
| `partner` | `partner_admin`, `partner_operator` |

Papel só é válido no tipo de organização correspondente (um `hr` não existe num `partner`).

## Permissões e guard

Papel mapeia pra um conjunto **fixo** de permissões (capabilities), declaradas em código —
ex.: `company.manage_members`, `agreements.write`, `invoices.approve_hr`,
`invoices.approve_finance`, `catalog.write`. O kernel define as permissões *da plataforma*;
cada módulo de negócio declara as suas próprias (spec 05).

Guard: uma dependency **`require_permission("...")`** (exposta via `core`) que resolve o papel
do `current_user` na `current_organization` e nega com **403** se a permissão faltar. Compõe
com `require_module` (spec 05) — um endpoint de app tipicamente exige as duas.

## Persona

Persona é derivada dos vínculos + tipo de organização ativa, e decide qual superfície de
frontend o usuário vê:

| Vínculo na org ativa | Persona |
|---|---|
| membro de `platform` | Plataforma (admin Widelab) |
| `company_admin`/`hr`/`finance`/`manager` numa `company` | Admin da Empresa |
| `collaborator` numa `company` | Colaborador |
| membro de `partner` | Parceiro |

## Endpoint de contexto

`GET /api/me/context` — o "bootstrap" que a casca do frontend consome:

```json
{
  "user": { "id": "...", "email": "...", "name": "..." },
  "memberships": [
    { "organization": { "id": "...", "type": "company", "name": "Widelab" }, "role": "collaborator" },
    { "organization": { "id": "...", "type": "partner",  "name": "Restaurante Gomes" }, "role": "partner_admin" }
  ],
  "active_organization_id": "...",
  "persona": "collaborator",
  "permissions": ["..."]
}
```

`active_organization_id` reflete o header `X-Organization-Id`; sem header, o backend escolhe
um default determinístico (ex.: primeiro vínculo) e o frontend confirma via seletor
(`frontend/05`). Módulos habilitados entram neste payload na spec 05.

## Endpoints de gestão de membros (`/api/memberships`)

| Método | Rota | Quem | Ação |
|---|---|---|---|
| `GET` | `/memberships` | `*_admin`/`hr` | lista membros da org ativa |
| `PATCH` | `/memberships/{id}` | `company_admin`/`platform_admin` | muda papel/status |

Criar membro é via convite (spec 06), não POST direto.

## Critérios de aceite

1. `require_permission` nega (403) quando o papel do usuário na org ativa não tem a permissão,
   e permite quando tem.
2. Um papel inválido pro tipo de organização é rejeitado na escrita do vínculo.
3. `GET /api/me/context` reflete corretamente múltiplos vínculos e a persona da org ativa.
4. Trocar `X-Organization-Id` muda a persona e as permissões retornadas sem novo login.
5. Um módulo de negócio consegue exigir `require_permission("...")` importando só de `core`.
