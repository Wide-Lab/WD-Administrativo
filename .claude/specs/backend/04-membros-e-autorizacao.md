# 04 — Membros e autorização

**Estado:** ⬜ não implementada. Bloqueada por `backend/03`.
**Depende de:** `backend/02-identidade-e-sessao.md`, `backend/03-organizacoes-e-tenancy.md`.
**Entrega:** `memberships` (usuário↔organização↔papel), o conjunto de papéis por tipo de
organização, o guard de permissão, a resolução de persona, e o endpoint de contexto que
alimenta a casca do frontend.

## Objetivo

Responder "quem é você **nesta** organização e o que pode fazer". Identidade (spec 02) é
global; autorização é sempre _dentro de uma organização_. O mesmo usuário pode ser
`collaborator` numa Empresa e `partner_admin` num Parceiro.

## Fora de escopo

- Entitlement de módulo (spec 05) — o guard de módulo é lá; aqui é papel/permissão.
- Papéis customizados por cliente — o conjunto de papéis é fixo por tipo de organização
  nesta fase; papéis definidos pelo cliente ganham spec própria se um dia forem pedidos.

## Modelo

`memberships`

| coluna            | tipo                     | nota |
| ----------------- | ------------------------ | ---- |
| `id`              | UUID (PK)                |      |
| `user_id`         | UUID → `users`           |      |
| `organization_id` | UUID → `organizations`   |      |
| `role`            | enum (ver abaixo)        |      |
| `status`          | enum `active`/`disabled` |      |
| `created_at`      | timestamptz              |      |

Único por `(user_id, organization_id)` — um papel por pessoa por organização nesta fase.

## Papéis por tipo de organização

| Tipo de org | Papéis                                                      |
| ----------- | ----------------------------------------------------------- |
| `platform`  | `platform_admin`                                            |
| `company`   | `company_admin`, `hr`, `finance`, `manager`, `collaborator` |
| `partner`   | `partner_admin`, `partner_operator`                         |

Papel só é válido no tipo de organização correspondente (um `hr` não existe num `partner`).

## Permissões e guard

Papel mapeia pra um conjunto **fixo** de permissões (capabilities), declaradas em código —
ex.: `company.manage_members`, `agreements.write`, `invoices.approve_hr`,
`invoices.approve_finance`, `catalog.write`. O kernel define as permissões _da plataforma_;
cada módulo de negócio declara as suas próprias (spec 05).

Guard: uma dependency **`require_permission("...")`** (exposta via `core`) que resolve o papel
do `current_user` na `current_organization` e nega com **403** se a permissão faltar. Compõe
com `require_module` (spec 05) — um endpoint de app tipicamente exige as duas.

## Persona

Persona é derivada dos vínculos + tipo de organização ativa, e decide qual superfície de
frontend o usuário vê:

| Vínculo na org ativa                                    | Persona                    |
| ------------------------------------------------------- | -------------------------- |
| membro de `platform`                                    | Plataforma (admin Widelab) |
| `company_admin`/`hr`/`finance`/`manager` numa `company` | Admin da Empresa           |
| `collaborator` numa `company`                           | Colaborador                |
| membro de `partner`                                     | Parceiro                   |

## Endpoints de contexto

Dois níveis, coerentes com o tenant no path:

`GET /api/me/contexto` — global, o "bootstrap" de roteamento e do seletor de organização:

```json
{
  "user": { "id": "...", "email": "...", "name": "..." },
  "memberships": [
    {
      "organization": { "id": "...", "type": "company", "name": "Widelab" },
      "role": "collaborator"
    },
    {
      "organization": {
        "id": "...",
        "type": "partner",
        "name": "Restaurante Gomes"
      },
      "role": "partner_admin"
    }
  ]
}
```

`GET /api/organizacoes/{orgId}/eu` — minha situação **nesta** organização, que a casca usa
pra montar navegação e liberar ações:

```json
{
  "role": "collaborator",
  "persona": "collaborator",
  "permissions": ["..."],
  "modules": ["refeicoes"]
}
```

Sem "organização ativa" no servidor nem default a adivinhar — qual org é sempre o `orgId` do
path. `modules` entra no payload por org na spec 05.

## Endpoints de gestão de membros

| Método  | Rota                                     | Quem                             | Ação                         |
| ------- | ---------------------------------------- | -------------------------------- | ---------------------------- |
| `GET`   | `/api/organizacoes/{orgId}/membros`      | `*_admin`/`hr`                   | lista membros da organização |
| `PATCH` | `/api/organizacoes/{orgId}/membros/{id}` | `company_admin`/`platform_admin` | muda papel/status            |

Criar membro é via convite (spec 06), não POST direto.

## Critérios de aceite

1. `require_permission` nega (403) quando o papel do usuário na org ativa não tem a permissão,
   e permite quando tem.
2. Um papel inválido pro tipo de organização é rejeitado na escrita do vínculo.
3. `GET /api/me/contexto` reflete corretamente múltiplos vínculos; `GET /api/organizacoes/{orgId}/eu`
   traz a persona e as permissões daquela organização.
4. Acessar `/api/organizacoes/{orgId}/eu` de organizações diferentes devolve personas e
   permissões diferentes, sem novo login.
5. Um módulo de negócio consegue exigir `require_permission("...")` importando só de `core`.
