# 05 — Módulos e entitlements

**Depende de:** `backend/03-organizacoes-e-tenancy.md`, `backend/04-membros-e-autorizacao.md`.
**Entrega:** o registro de módulos, a tabela de entitlement por Empresa, o guard
`require_module`, e o **contrato que um app de negócio cumpre pra plugar** no superapp.

## Objetivo

Fazer valer a decisão comercial da `00-visao-geral.md`: **cada Empresa só enxerga os módulos
que contratou, negação por padrão, imposto no backend (403) e não só escondido no frontend.**
Vender um módulo novo pra um cliente é ligar um flag, sem deploy.

## Fora de escopo

- Os módulos de negócio em si (Refeições é fase 2, Carro é fase 3). Esta spec entrega o
  mecanismo, com `meals` e `fleet` existindo apenas como chaves registradas.
- Cobrança/billing da plataforma (quanto a Widelab cobra por módulo) — spec própria futura.

## Registro de módulos

Em `core`, um `ModuleRegistry`. Cada módulo de negócio declara um descritor e se registra na
subida — **uma linha em `mount_routes`**, coerente com a regra da `backend/01-fundacao.md`:

```python
ModuleDescriptor(
    key="meals",                    # estável, kebab/snake, é PK de várias coisas
    name="Refeições",
    personas=["company_admin", "collaborator", "partner"],
    permissions=["catalog.write", "invoices.approve_hr", ...],
    nav={...},                       # metadados de navegação p/ o frontend
)
```

O registry é a fonte da lista de módulos que a plataforma sabe oferecer. Registrar um módulo
**não toca `core`** além do descritor; um módulo nunca aparece pra um tenant sem entitlement.

## Modelo

`module_entitlements`

| coluna | tipo | nota |
|---|---|---|
| `id` | UUID (PK) | |
| `organization_id` | UUID → `organizations` (type=company) | |
| `module_key` | text | referencia uma chave do registry |
| `granted_at` | timestamptz | |
| `granted_by` | UUID → `users` | quem (platform_admin) liberou |

Único por `(organization_id, module_key)`. **Presença da linha = habilitado. Ausência =
negado.** Não há coluna booleana — desligar é apagar (ou expirar, se um dia precisar de
histórico; fora de escopo agora).

## Guard

`require_module("meals")` — dependency (exposta via `core`) que 403 se a `current_organization`
(type=company) não tiver a linha de entitlement. Todo endpoint de um módulo de negócio o
aplica; compõe com `require_permission` (spec 04):

```python
@router.post("/meals/...", dependencies=[Depends(require_module("meals")),
                                          Depends(require_permission("catalog.write"))])
```

## Endpoints

Gestão de entitlement (só `platform_admin`):

| Método | Rota | Ação |
|---|---|---|
| `GET` | `/api/organizations/{id}/modules` | módulos habilitados da Empresa + catálogo disponível |
| `PUT` | `/api/organizations/{id}/modules/{key}` | habilita (idempotente) |
| `DELETE` | `/api/organizations/{id}/modules/{key}` | desabilita |

Contexto do usuário — `GET /api/me/context` (spec 04) passa a incluir os módulos habilitados
da org ativa, pra casca do frontend montar navegação:

```json
"modules": ["meals"]
```

## Contrato do app de negócio (o que "plugar" significa)

Um módulo de negócio, pra existir no superapp, precisa:

1. registrar um `ModuleDescriptor` (chave, personas, permissões, nav);
2. montar rotas em `/api/<key>/*`, todas atrás de `require_module(<key>)`;
3. escopar todo dado por `organization_id` via o helper tenant-scoped (spec 03);
4. declarar suas permissões e checá-las com `require_permission` (spec 04);
5. depender **só** de `core` e dos contracts do kernel — nunca de outro módulo de negócio.

Cumprido isso, adicionar Refeições ou Carro não toca no núcleo.

## Critérios de aceite

1. Endpoint de um módulo responde 403 pra Empresa sem entitlement, mesmo com papel/permissão
   corretos — a negação é do backend, não do frontend.
2. `PUT` do entitlement é idempotente; `DELETE` volta a negar.
3. `GET /api/me/context` lista exatamente os módulos habilitados da org ativa.
4. Registrar um módulo novo no `ModuleRegistry` não exige mudança em `core` além do descritor
   e de uma linha em `mount_routes`.
5. Só `platform_admin` altera entitlement; qualquer outro papel recebe 403.
