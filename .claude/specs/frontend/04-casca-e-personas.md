# 04 — Casca e personas

**Estado:** ⬜ não implementada. `frontend/03` ✅; bloqueada pelo `access` (`backend/04`+`05`).
É esta spec que decide a home de verdade e aposenta a `/` placeholder da `03`.
**Depende de:** `frontend/03-login-e-sessao.md`, `backend/04-membros-e-autorizacao.md`,
`backend/05-modulos-e-entitlements.md`.
**Entrega:** o app shell, os route groups por persona, e a navegação derivada de
vínculos + módulos habilitados. É onde o superapp vira "superapp".

## Objetivo

Uma única app Next mostra a cara certa pra cada pessoa. A casca lê `GET /api/me/contexto` e
`GET /api/organizacoes/{orgId}/eu`
uma vez e, a partir da **persona** e dos **módulos habilitados**, monta navegação e libera
rotas. O usuário só vê o que tem direito — e o backend recusa o resto (403), então a casca
é ergonomia, não segurança.

## Fora de escopo

Troca de organização (spec 05) — aqui assume-se uma org ativa já resolvida. As telas
_internas_ de cada módulo de negócio (Refeições, Carro) são das fases 2+; esta spec entrega a
casca vazia por persona com navegação, estados e guarda.

## Estrutura de rotas (`src/app/`)

```
app/
  (publico)/entrar, /convites/[token], /parceiros/cadastro   # público (specs 03, 06)
  plataforma/...                    # persona Plataforma (Widelab): tenants, entitlements — cross-tenant, sem orgId
  organizacoes/[orgId]/
    layout.tsx                      # carrega /api/organizacoes/{orgId}/eu, resolve a persona e monta a casca
    page.tsx                        # home da persona
    refeicoes/...                   # módulo (fase 2), sob o orgId
    frota/...                       # módulo (fase 3), sob o orgId
```

Coerente com o tenant no path (backend spec 03): tudo que é de uma organização vive sob
`/organizacoes/[orgId]/`. O `layout.tsx` desse nível lê `GET /api/organizacoes/{orgId}/eu`,
**resolve a persona** (Admin da Empresa / Parceiro / Colaborador, conforme tipo da org +
papel) e monta a casca certa (masthead, navegação lateral ou inferior). A área da Plataforma
é cross-tenant e fica fora do `orgId`. A persona Colaborador é mobile-first (candidata a PWA).

## Feature `context` (`features/context/`)

- `api.ts` — `getContext()` → `GET /api/me/contexto` (global: usuário + vínculos);
  `getOrgContext(orgId)` → `GET /api/organizacoes/{orgId}/eu` (persona, permissões, módulos
  daquela org).
- `use-context.ts` / `use-org-context.ts` — TanStack Query; juntos expõem
  `{ user, memberships }` e `{ persona, permissions, modules }` da org da URL. Fonte única de
  autorização no cliente.
- `nav.ts` (puro, testado) — dado `persona` + `modules` + descritores de nav dos módulos,
  produz a lista de itens de navegação. Módulo sem entitlement **não** entra na lista.

## Navegação orientada a módulo

Os itens de navegação dos módulos de negócio vêm dos descritores expostos no contexto
(`modules` + metadados de nav do `ModuleDescriptor`, backend spec 05). Ligar um módulo pra um
tenant faz o item aparecer sem deploy de frontend; desligar, sumir.

## Guarda de persona e módulo

- Acessar um group de persona sem vínculo compatível → redireciona pra home da persona real
  do usuário.
- Acessar a rota de um módulo não habilitado → tela "módulo não disponível" (e o backend já
  responderia 403 de qualquer forma).
- `permissions` do contexto escondem/desabilitam ações dentro de uma persona (ex.: só
  `finance` vê "aprovar no financeiro") — sempre espelhando um guard real no backend.

## Home por persona

Cada persona tem uma home mínima nesta spec (placeholder com a navegação e o nome da org
ativa) — o conteúdo real chega com os módulos. A persona `collaborator` já nasce mobile-first.

## Critérios de aceite

1. Com um contexto de `collaborator` numa Empresa com `refeicoes` habilitado, a casca do
   Colaborador aparece com o item de Refeições; sem `refeicoes`, o item some.
2. Um `platform_admin` vê a persona Plataforma; um `partner_admin`, a do Parceiro.
3. Rota de módulo não habilitado mostra "módulo não disponível" e nunca dispara chamada que
   dependa dele.
4. `features/context/nav.ts` é função pura com teste cobrindo persona × módulos.
5. Ações condicionadas a permissão só aparecem quando a permissão está no contexto.
