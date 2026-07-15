# 03 — Login e sessão

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
