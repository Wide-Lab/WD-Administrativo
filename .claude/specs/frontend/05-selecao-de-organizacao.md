# 05 — Seleção de organização

**Estado:** ⬜ não implementada. Bloqueada por `frontend/04`.
**Depende de:** `frontend/04-casca-e-personas.md`, `backend/03-organizacoes-e-tenancy.md`.
**Entrega:** a troca de organização ativa quando um usuário pertence a mais de uma —
o Parceiro que atende N Empresas, ou a pessoa que é Colaborador aqui e admin ali.

## Objetivo

O backend escopa tudo pela organização do path `/api/organizacoes/{orgId}/...` (backend spec
03). No frontend, a organização ativa **é o `orgId` da URL** — trocar de organização é
navegar. Esta spec cobre como o usuário escolhe e troca esse `orgId`, sem novo login.

## Fora de escopo

Provisionamento de organização (é do `platform_admin`, backend spec 03) e associação por
convênio (spec 06). Aqui só se **escolhe entre** organizações onde o usuário já tem vínculo.

## Organização ativa = URL

- A org ativa é o `orgId` do path — nenhum header, nenhum store de "org ativa". O cliente de
  fetch **não** injeta `X-Organization-Id`; as chamadas já vão pra `/api/organizacoes/{orgId}/...`.
- Trocar de organização é **navegar** pra `/organizacoes/{outroId}/...`. Como o `orgId` das
  queries muda, o TanStack Query naturalmente troca o cache por org (chaves incluem `orgId`) —
  não há dado da org anterior servido pra outra. A persona pode mudar na troca (Colaborador
  numa Empresa → admin num Parceiro); o `layout.tsx` de `/organizacoes/[orgId]` re-resolve.
- Um `localStorage` guarda só o **último `orgId` visitado**, usado apenas pra decidir pra
  onde redirecionar logo após o login.

## Resolução inicial (pós-login)

Como não há org na URL logo após `/entrar`, um passo decide o redirect:

- 0 vínculos → tela "sem acesso" (raro; conta sem membership).
- 1 vínculo → redireciona direto pra `/organizacoes/{orgId}`, **sem** seletor.
- 2+ vínculos → usa o último `orgId` do `localStorage` se ainda for um vínculo válido; senão,
  o primeiro vínculo. O seletor (abaixo) permite trocar depois.

## Seletor (UI)

Um controle no masthead da casca (só aparece com 2+ vínculos), alimentado por `memberships`
de `GET /api/me/contexto`: lista as organizações do usuário com tipo e nome (ex.: "Widelab —
Colaborador", "Restaurante Gomes — Parceiro"), marca a org do `orgId` atual, e ao selecionar
**navega** pra `/organizacoes/{outroId}`. Em telas de Parceiro que atende muitas Empresas, o
mesmo padrão vale pra filtrar "por Empresa" dentro da persona Parceiro, mas isso é refinamento
dos módulos, não desta spec.

## Critérios de aceite

1. Usuário com um vínculo nunca vê o seletor; com dois ou mais, vê e consegue trocar.
2. Trocar de organização navega pra `/organizacoes/{outroId}`, re-resolve a persona, e nenhuma
   query continua servindo dado da organização anterior (chave de cache inclui `orgId`).
3. Nenhuma chamada envia `X-Organization-Id`; a org viaja no path da URL.
4. O último `orgId` visitado persiste e orienta o redirect pós-login; se o vínculo deixar de
   existir, cai no primeiro vínculo sem quebrar.
5. Navegar pra um `orgId` sem vínculo (403 do backend) leva à reseleção, não a uma tela
   quebrada.
