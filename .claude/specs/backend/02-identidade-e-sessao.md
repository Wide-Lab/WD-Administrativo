# 02 — Identidade e sessão

**Estado:** ✅ implementada (`438463d`, 2026-07-16). Ver `Como ficou` no fim.
**Depende de:** `backend/01-fundacao.md`.
**Entrega:** o módulo `auth` — identidade global de pessoa (uma pessoa, um e-mail, um
login), autenticação por senha, sessão em cookie, `GET /api/me`, e a **porta trocável**
de autenticação que deixa o SSO da Central plugável depois sem tocar autorização.

## Objetivo

Dar ao superapp uma identidade **própria e global**. Um usuário é uma pessoa, não um papel:
não tem organização nem permissão — essas relações são do módulo `access` (specs 03–04). Um
mesmo login pode ser, ao mesmo tempo, Colaborador de uma Empresa e admin de um Parceiro; quem
resolve isso são os vínculos, não a identidade.

Este é o primeiro módulo do **kernel da plataforma**. Módulos de negócio (Refeições, Carro)
nunca importam `auth` diretamente — consomem `current_user`, exposto por `core`.

## Fora de escopo

- Organizações, papéis, permissões (specs 03–04).
- Recuperação de senha ("esqueci minha senha") e política de expiração/rotação de sessão —
  cada um ganha spec própria quando fizer falta. Aqui a senha é definida (pelo onboarding,
  spec 06) e trocada logado; sessão expira e exige novo login.
- Revogação de sessão antes da expiração — fora de escopo, como na Central.

## Modelo

`users`

| coluna                      | tipo                     | nota                                                                                     |
| --------------------------- | ------------------------ | ---------------------------------------------------------------------------------------- |
| `id`                        | UUID (PK)                |                                                                                          |
| `email`                     | CITEXT, único            | e-mail é sempre CITEXT, nunca `String`+`.lower()`                                        |
| `name`                      | text                     |                                                                                          |
| `password_hash`             | text, nullable           | Argon2id. Nulo enquanto convidado sem senha definida, ou se autenticar só via SSO futuro |
| `status`                    | enum `active`/`disabled` |                                                                                          |
| `created_at` / `updated_at` | timestamptz              |                                                                                          |

Sem `organization_id`, sem `role`. Identidade é global.

## Autenticação e sessão

- **Senha:** Argon2id (`argon2-cffi`), nunca bcrypt. Hash e verificação em `core/security.py`.
- **Sessão:** JWT assinado pela própria aplicação (HS256 com segredo do servidor basta —
  é um monólito, há um único verificador; a Central usa RS256 porque _outros apps_ validam,
  o que não é o nosso caso). Entregue num cookie **httpOnly, Secure, SameSite=Lax**, expiração
  configurável (default 12h). O payload carrega só `sub` (user_id) e `exp` — **nada de papel
  ou organização no token** (isso muda a cada request e é resolvido pelo `access`).
- `core/security.py` ganha: `hash_password`, `verify_password`, `issue_session(user_id)`,
  `read_session(token) -> user_id`, e a dependency **`current_user`** (lê o cookie, valida,
  devolve o usuário; 401 se ausente/inválido). `current_user` mora em `core` justamente pra
  módulos de negócio a consumirem sem importar `auth`.

## Porta trocável de autenticação

Em `core`, uma porta `Authenticator` com `authenticate(credentials) -> UserId`. A
implementação desta spec é `PasswordAuthenticator` (confere senha na tabela `users`). Ligar
"entrar com a Widelab" (Central, JWT RS256 via JWKS) no futuro é adicionar um
`CentralSsoAuthenticator` que valida o token da Central e mapeia pro `user` local — **sem
tocar** em nada de `access`/autorização. Essa fronteira é a decisão registrada na
`00-visao-geral.md`.

## Endpoints

| Método | Rota               | Ação                                                                          |
| ------ | ------------------ | ----------------------------------------------------------------------------- |
| `POST` | `/api/auth/login`  | `{email, password}` → valida via `Authenticator`, emite cookie de sessão, 200 |
| `POST` | `/api/auth/logout` | limpa o cookie, 204                                                           |
| `GET`  | `/api/me`          | identidade do usuário logado: `{id, email, name}`. 401 se não logado          |
| `PUT`  | `/api/me/password` | logado, `{current_password, new_password}` → troca senha                      |

`GET /api/me` devolve **só identidade**. Vínculos, personas e módulos habilitados vêm de
`GET /api/me/contexto` e `GET /api/organizacoes/{orgId}/me` (specs 04/05).

## CLI

Como na Central, um comando pra criar usuário fora de fluxo (bootstrap do primeiro
`platform_admin`): `python -m src.modules.auth.cli create-user --email … --name …` (pede
senha via prompt). O vínculo com a organização plataforma é dado pela spec 03/04.

## Critérios de aceite

1. `POST /api/auth/login` com credenciais válidas seta cookie httpOnly e `GET /api/me`
   passa a responder a identidade; com credenciais inválidas, 401 e nenhum cookie.
2. `GET /api/me` sem cookie responde 401.
3. Senha nunca aparece em log nem em resposta; `password_hash` é Argon2id.
4. O token de sessão não contém papel nem organização.
5. Trocar `PasswordAuthenticator` por outra implementação de `Authenticator` não exige
   mudança fora do módulo `auth`.
6. `current_user` é importável de `core` e usável por qualquer módulo sem importar `auth`.

## Como ficou

Todos os critérios batem. O que a implementação resolveu e a spec não previa:

- **A porta `UserReader`, e o registro dela em `mount_routes`.** O critério 6 (`current_user`
  no `core`, sem importar `auth`) esbarrou num problema que a spec não enxergou: `current_user`
  precisa **ler a tabela `users`**, que é do `auth` — e `core` não pode importar módulo. A
  saída foi inverter a dependência: `core/security/identity.py` declara a porta `UserReader`, e
  `mount_routes` chama `set_user_reader_factory(SqlAlchemyUserReader)`, entregando a
  implementação ao `core` no boot. É o **único** caso em que um módulo tem duas linhas no
  `mount_routes`, e é privilégio de kernel — app de negócio consome `CurrentUserDep` e pronto.
- **`core/security.py` é um pacote**, não um arquivo (ver `Como ficou` da `01`): a superfície
  pública sai do `__init__` — `CurrentUser`, `CurrentUserDep`, `Authenticator`, `UserReader`,
  `hash_password`/`verify_password`, `issue_session`/`read_session`,
  `set_session_cookie`/`clear_session_cookie`. **É daqui que qualquer módulo consome identidade.**
- **`POST /api/auth/login` responde 200 sem corpo** — a identidade vem do `GET /api/me`, que o
  frontend já chama de qualquer forma; devolver o usuário no login seria uma segunda fonte da
  verdade.
- **A escolha do autenticador é uma linha:** `get_authenticator()` em
  `modules/auth/adapters/http/dependencies.py`. Rotas e use cases falam com a porta
  `Authenticator[PasswordCredentials]`, nunca com a implementação — é o ponto exato onde o
  `CentralSsoAuthenticator` entra.
- **Migration `0001_users`**, com `CREATE EXTENSION IF NOT EXISTS citext`, enum `user_status`
  e índice único `ix_users_email`. `password_hash` nullable, como o modelo previa (convidado
  sem senha, spec `06`).
- **CLI:** `python -m src.modules.auth.cli create-user --email … --name …`, como especificado.
