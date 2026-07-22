# 06 — Convites e onboarding

**Estado:** ✅ implementada (2026-07-16). Fecha a fase 1 do backend. Ver [`como-ficou.md`](./como-ficou.md).
**Depende de:** `backend/02-identidade-e-sessao/spec.md`, `backend/03-organizacoes-e-tenancy/spec.md`,
`backend/04-membros-e-autorizacao/spec.md`.
**Entrega:** os dois fluxos de entrada de gente no sistema — **Colaborador convidado** por
uma Empresa e **Parceiro auto-cadastrado** — mais o vínculo do Parceiro a uma Empresa.

## Objetivo

Como uma pessoa passa a ter login e vínculo. São dois caminhos deliberadamente diferentes,
que a `00-visao-geral.md` pediu pra separar de "membros":

- **Colaborador / staff da Empresa:** não se auto-cadastra. É **convidado** por quem tem
  `company_admin`/`hr`, com um papel já definido. Aceita o convite e define a senha.
- **Parceiro:** **se cadastra uma vez** (auto-registro cria a organização `partner` + o
  primeiro `partner_admin`), e depois é **associado** a Empresas por convênio.

## Fora de escopo

- Recuperação de senha ("esqueci") — spec própria futura (ver spec 02).
- Aprovação/curadoria de Parceiros pela plataforma antes de operar — se for necessário um
  gate, entra como status do convênio; o fluxo de aprovação em si é spec futura.

## Modelo

`invitations`

| coluna | tipo | nota |
|---|---|---|
| `id` | UUID (PK) | |
| `email` | CITEXT | |
| `organization_id` | UUID → `organizations` | pra qual org o convite dá vínculo |
| `role` | enum | papel que o vínculo terá ao aceitar |
| `token` | text, único | opaco, uso único |
| `status` | enum `pending`/`accepted`/`revoked`/`expired` | |
| `expires_at` | timestamptz | |
| `invited_by` | UUID → `users` | |
| `created_at` | timestamptz | |

## Fluxo A — Colaborador convidado

1. `POST /api/organizacoes/{orgId}/convites` (`company_admin`/`hr`) `{email, role}` na Empresa
   `{orgId}` → cria `invitation` pending com token e expiração; dispara e-mail (envio via
   porta em `core`; o provedor concreto é detalhe de infra, não desta spec).
2. `GET /api/convites/{token}` (público) → dados públicos mínimos pra tela de aceite (nome da
   Empresa, e-mail, papel). 404/410 se inválido/expirado.
3. `POST /api/convites/{token}/aceitar` `{name?, password}`:
   - se **não** existe `user` pro e-mail → cria via porta `UserDirectory` (definida em `core`,
     implementada por `auth`) e define a senha;
   - se **já** existe → apenas cria o `membership`;
   - cria o `membership (user, organization, role)`, marca o convite `accepted`, emite sessão.
   Idempotente por token: reusar um token já aceito não cria vínculo duplicado.

## Fluxo B — Parceiro auto-cadastrado

1. `POST /api/parceiros/cadastro` `{company_name, document?, admin: {name, email, password}}`
   (rota pública) → numa transação: cria `organization(type=partner)`, cria o `user` (via
   `UserDirectory`) e o `membership(partner_admin)`, emite sessão. E-mail duplicado → 409.
2. A associação a uma Empresa é o convênio da spec 03: `company_admin` faz
   `POST /api/organizacoes/{orgId}/convenios {partner_id}`. Alternativamente, uma Empresa pode **convidar** um
   Parceiro que ainda não existe reusando o Fluxo A com `organization` do tipo convite de
   parceria — decidir na implementação; o mínimo desta spec é auto-registro + associação por
   convênio.

## Regras de segurança

- Token opaco (ex.: 32 bytes url-safe), **uso único**, expira (default 7 dias).
- Aceitar convite não revela se o e-mail já tinha conta (resposta uniforme).
- `POST /api/parceiros/cadastro` e `aceitar` respeitam a mesma política de senha do login (spec 02).
- Convite é escopado à organização de quem convida; `hr` de uma Empresa não convida pra outra.

## Critérios de aceite

1. Convite → aceite cria exatamente um `user` (se novo) e um `membership` com o papel do
   convite; reaceitar o mesmo token não duplica nada e não reabre sessão indevidamente.
2. Convite expirado ou revogado recusa o aceite (410) e não cria vínculo.
3. `POST /api/parceiros/cadastro` cria org + admin + sessão numa transação atômica; e-mail
   repetido dá 409 sem criar organização órfã.
4. Um `hr` não consegue convidar para uma organização que não é a sua (403).
5. Criação de usuário no onboarding passa pela porta `UserDirectory`, sem `onboarding`
   importar `auth` diretamente.
