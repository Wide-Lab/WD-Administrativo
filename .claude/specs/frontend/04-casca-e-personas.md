# 04 — Casca e personas

**Depende de:** `frontend/03-login-e-sessao.md`, `backend/04-membros-e-autorizacao.md`,
`backend/05-modulos-e-entitlements.md`.
**Entrega:** o app shell, os route groups por persona, e a navegação derivada de
vínculos + módulos habilitados. É onde o superapp vira "superapp".

## Objetivo

Uma única app Next mostra a cara certa pra cada pessoa. A casca lê `GET /api/me/context`
uma vez e, a partir da **persona** e dos **módulos habilitados**, monta navegação e libera
rotas. O usuário só vê o que tem direito — e o backend recusa o resto (403), então a casca
é ergonomia, não segurança.

## Fora de escopo

Troca de organização (spec 05) — aqui assume-se uma org ativa já resolvida. As telas
*internas* de cada módulo de negócio (Refeições, Carro) são das fases 2+; esta spec entrega a
casca vazia por persona com navegação, estados e guarda.

## Route groups (`src/app/`)

```
app/
  (auth)/login, /convite/[token], /parceiro/cadastro   # público (specs 03, 06)
  (platform)/...      # persona Plataforma (admin Widelab): tenants, entitlements
  (admin)/...         # persona Admin da Empresa: membros, convênios, config de módulos
  (partner)/...       # persona Parceiro
  (collaborator)/...  # persona Colaborador (mobile-first; candidato a PWA depois)
```

Cada group tem seu `layout.tsx` com a casca daquela persona (masthead, navegação lateral ou
inferior). O conteúdo dos módulos entra dentro do group da persona a que serve.

## Feature `context` (`features/context/`)

- `api.ts` — `getContext()` → `GET /api/me/context`.
- `use-context.ts` — TanStack Query; expõe `{ user, memberships, activeOrg, persona,
  permissions, modules }`. Fonte única de autorização no cliente.
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

1. Com um contexto de `collaborator` numa Empresa com `meals` habilitado, a casca do
   Colaborador aparece com o item de Refeições; sem `meals`, o item some.
2. Um `platform_admin` vê a persona Plataforma; um `partner_admin`, a do Parceiro.
3. Rota de módulo não habilitado mostra "módulo não disponível" e nunca dispara chamada que
   dependa dele.
4. `features/context/nav.ts` é função pura com teste cobrindo persona × módulos.
5. Ações condicionadas a permissão só aparecem quando a permissão está no contexto.
