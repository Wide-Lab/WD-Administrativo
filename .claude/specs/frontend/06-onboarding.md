# 06 — Onboarding

**Depende de:** `frontend/03-login-e-sessao.md`, `backend/06-convites-e-onboarding.md`.
**Entrega:** as telas públicas de entrada — aceite de convite (Colaborador/staff) e
auto-cadastro de Parceiro — mais o primeiro acesso por persona.

## Objetivo

Fechar o ciclo dos dois fluxos da backend spec 06 no frontend: transformar um link de convite
ou um cadastro de parceiro numa sessão ativa, caindo já na persona certa.

## Fora de escopo

Convidar/gerir membros de dentro da Empresa (é ação da persona Admin, entra com o módulo de
gestão) e recuperação de senha (spec futura). Aqui só as telas públicas de *entrada*.

## Telas (group `(auth)`, público)

- **`/convite/[token]`** — aceite de convite:
  1. busca `GET /api/invitations/{token}`; se inválido/expirado, tela clara de "convite
     expirado" com caminho pra pedir novo, **sem** vazar se o e-mail tem conta.
  2. mostra Empresa, e-mail (read-only) e papel; formulário de `name?` + `password` (+
     confirmação), validado por zod com a política de senha combinada.
  3. `POST /api/invitations/{token}/accept` → no sucesso, sessão emitida (cookie), redireciona
     pra home da persona do papel aceito.

- **`/parceiro/cadastro`** — auto-registro de Parceiro:
  formulário `{company_name, document?, admin: {name, email, password}}`, validado por zod;
  `POST /api/partners/signup`; e-mail já usado → mensagem de conflito (409) apontando pro
  login; no sucesso, sessão emitida e cai na home do Parceiro.

## Primeiro acesso

Ao entrar pela primeira vez, o usuário cai direto na home da sua persona (casca da spec 04),
com a organização ativa já resolvida (spec 05). Sem wizard nesta fase — o mínimo é: logou,
está no lugar certo.

## Reuso

Formulário de senha (regras, confirmação, medidor opcional) é um componente compartilhado
entre `/convite/[token]`, `/parceiro/cadastro` e a troca de senha logada (spec 03) — mora em
`features/auth/components`, não duplicado.

## Critérios de aceite

1. Link de convite válido leva a uma tela que, ao definir senha, autentica e cai na persona
   correta; link expirado mostra estado claro e não autentica.
2. Auto-cadastro de Parceiro cria a conta e entra na persona Parceiro; e-mail repetido mostra
   conflito e leva ao login, sem estado órfão na tela.
3. As três telas com campo de senha usam o mesmo componente e a mesma validação zod.
4. Nenhuma tela de onboarding revela existência prévia de conta por e-mail.
5. Após onboarding, recarregar mantém a sessão e a persona (integra com specs 03 e 05).
