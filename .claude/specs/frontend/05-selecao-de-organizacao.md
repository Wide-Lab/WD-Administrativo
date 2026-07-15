# 05 — Seleção de organização

**Depende de:** `frontend/04-casca-e-personas.md`, `backend/03-organizacoes-e-tenancy.md`.
**Entrega:** a troca de organização ativa quando um usuário pertence a mais de uma —
o Parceiro que atende N Empresas, ou a pessoa que é Colaborador aqui e admin ali.

## Objetivo

O backend escopa tudo pela organização ativa, lida do header `X-Organization-Id` (backend
spec 03). Esta spec dá ao usuário o controle desse header: qual organização ele está "vendo"
agora, trocável sem novo login.

## Fora de escopo

Provisionamento de organização (é do `platform_admin`, backend spec 03) e associação por
convênio (spec 06). Aqui só se **escolhe entre** organizações onde o usuário já tem vínculo.

## Estado de organização ativa

- Um store de cliente (`features/context/active-org.ts`) guarda o `activeOrganizationId`,
  persistido em `localStorage`.
- O cliente de fetch injeta `X-Organization-Id: <activeOrganizationId>` em toda chamada
  `/api/*`.
- Trocar de organização: seta o store, **invalida** `me/context` e todas as queries de dados,
  e leva o usuário pra home da persona resultante (a persona pode mudar — de Colaborador numa
  Empresa pra admin num Parceiro).

## Resolução inicial

- 0 vínculos → tela "sem acesso" (raro; conta sem membership).
- 1 vínculo → seleciona automaticamente, **sem** mostrar seletor.
- 2+ vínculos → usa o último escolhido (localStorage) se ainda válido; senão, um default
  determinístico do backend, confirmável pelo seletor.

## Seletor (UI)

Um controle no masthead da casca (só aparece com 2+ vínculos): lista as organizações do
usuário com tipo e nome (ex.: "Widelab — Colaborador", "Restaurante Gomes — Parceiro"),
marca a ativa, troca ao selecionar. Em telas de Parceiro que atende muitas Empresas, o mesmo
padrão vale pra filtrar "por Empresa" dentro da persona Parceiro, mas isso é refinamento dos
módulos, não desta spec.

## Critérios de aceite

1. Usuário com um vínculo nunca vê o seletor; com dois ou mais, vê e consegue trocar.
2. Trocar de organização re-busca o contexto, troca a persona quando for o caso, e nenhuma
   query continua servindo dado da organização anterior (cache invalidado).
3. Todo request sai com `X-Organization-Id` da organização ativa.
4. A escolha persiste entre recarregamentos; se o vínculo deixar de existir, cai no default
   sem quebrar.
5. Um `X-Organization-Id` inválido/sem vínculo (403 do backend) derruba pra reseleção, não
   pra tela quebrada.
