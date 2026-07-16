# 03 — Login e sessão

**Estado:** ✅ implementada (`3b76bf8`, 2026-07-16). Ver `Como ficou` no fim.
**Depende de:** `frontend/01-fundacao.md`, `frontend/02-design-system.md`,
`backend/02-identidade-e-sessao.md`.
**Entrega:** a tela de login, o ciclo de vida de sessão no cliente, e o cliente da API de
identidade — a porta de entrada de qualquer persona.

## Objetivo

Autenticar e manter a sessão. A sessão vive num cookie httpOnly emitido pelo backend (spec
backend 02), então o frontend **não guarda token** — só reage a estar/não estar logado, lido
via `GET /api/me`.

## Fora de escopo

Escolha de organização (spec 05) e montagem da casca por persona (spec 04). Aqui: logar,
deslogar, saber se está logado, e mandar quem não está pro login.

## Feature `auth` (`features/auth/`)

- `schema.ts` — zod dos formulários (`loginSchema: {email, password}`).
- `api.ts` — `login`, `logout`, `getMe`; sempre `credentials: 'include'`, caminhos `/api/*`.
- `use-session.ts` — hook TanStack Query sobre `GET /api/me`: expõe
  `{ user, isLoading, isAuthenticated }`. É a fonte única de "estou logado?".
- `use-login.ts` / `use-logout.ts` — mutations; no sucesso do login, invalida a query de
  sessão e o contexto (spec 04); no logout, limpa o cache e manda pra `/entrar`.

## Telas

- **`/entrar`** — cartão central sobre `bg`, logo, campos e-mail/senha, botão primário
  (gradiente azul), erro inline em `danger` sem revelar qual campo falhou ("credenciais
  inválidas"). Estado de carregando no submit. Ao logar, redireciona pro destino guardado ou
  pra home da persona (resolvida na spec 04).

## Guarda de rota

Um wrapper (client) que, montado nas áreas autenticadas: se `use-session` diz não-logado,
redireciona pra `/entrar?next=<rota>`; enquanto carrega, mostra skeleton, não flasheia
conteúdo. Respostas **401** de qualquer chamada de API derrubam a sessão e mandam pro login
(interceptor no cliente de fetch).

## Critérios de aceite

1. Login válido seta o cookie (pelo backend) e passa a renderizar área autenticada; inválido
   mostra erro genérico e permanece em `/entrar`.
2. Recarregar a página mantém a sessão (cookie httpOnly + `GET /api/me`), sem token no JS.
3. Logout limpa o cache do TanStack Query e volta pra `/entrar`.
4. Um 401 em qualquer request redireciona pro login preservando `next`.
5. Nada de conteúdo autenticado pisca antes da checagem de sessão.

## Como ficou

Todos os critérios batem. O que a implementação decidiu, além do texto:

- **A guarda tem duas metades:** `RequireSession` (manda o deslogado pra
  `/entrar?next=<rota>`, mostrando skeleton enquanto carrega — critério 5) e
  `RedirectIfAuthenticated` (tira o logado de `/entrar`). A segunda não estava na spec e é o
  que impede a tela de login de virar um beco pra quem já tem sessão.
- **O interceptor de 401 mora no `QueryCache` dos providers**, não no `apiFetch`: o cliente de
  fetch só traduz erro (`ApiError` com `status`/`code`), e a política de "401 derruba a sessão"
  fica na camada que conhece o router e o cache. Uma mutation pode optar por fora com
  `meta: { skipUnauthorizedRedirect: true }` — é o que o logout usa, já que ali o 401 é
  esperado e não deve virar redirect duplo.
- **O logout limpa o cache no `onSettled`, não no `onSuccess`.** Se o cookie já expirou, a
  chamada falha — mas a intenção de sair vale igual, e deixar dado de outro usuário no cache
  seria pior que engolir o erro.
- **`next` é validado** (`lib/next-path.ts`, com teste): só caminho relativo interno passa, pra
  o parâmetro não virar open redirect. O mapeamento de erro pra mensagem genérica também é
  função pura testada (`lib/login-error.ts`) — credenciais inválidas nunca revelam qual campo
  falhou, como a spec exige.
- **`/entrar`** tem o `ledger-backdrop`, um fundo decorativo de feature; o destino pós-login é
  a `/` placeholder, porque a home por persona é da `04` — é lá que o "destino guardado ou home
  da persona" fecha de verdade.
