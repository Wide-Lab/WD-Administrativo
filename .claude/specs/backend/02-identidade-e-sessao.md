# 02 — Identidade e sessão

**Depende de:** `backend/01-fundacao.md`.
**Entrega:** o módulo `auth` — identidade global de pessoa (uma pessoa, um e-mail, um
login), autenticação por senha, sessão em cookie, `GET /api/auth/me`, e a **porta trocável**
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

| coluna | tipo | nota |
|---|---|---|
| `id` | UUID (PK) | |
| `email` | CITEXT, único | e-mail é sempre CITEXT, nunca `String`+`.lower()` |
| `name` | text | |
| `password_hash` | text, nullable | Argon2id. Nulo enquanto convidado sem senha definida, ou se autenticar só via SSO futuro |
| `status` | enum `active`/`disabled` | |
| `created_at` / `updated_at` | timestamptz | |

Sem `organization_id`, sem `role`. Identidade é global.

## Autenticação e sessão

- **Senha:** Argon2id (`argon2-cffi`), nunca bcrypt. Hash e verificação em `core/security.py`.
- **Sessão:** JWT assinado pela própria aplicação (HS256 com segredo do servidor basta —
  é um monólito, há um único verificador; a Central usa RS256 porque *outros apps* validam,
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

## Endpoints (`/api/auth`)

| Método | Rota | Ação |
|---|---|---|
| `POST` | `/auth/login` | `{email, password}` → valida via `Authenticator`, emite cookie de sessão, 200 |
| `POST` | `/auth/logout` | limpa o cookie, 204 |
| `GET` | `/auth/me` | identidade do usuário logado: `{id, email, name}`. 401 se não logado |
| `POST` | `/auth/password` | logado, `{current_password, new_password}` → troca senha |

`GET /auth/me` devolve **só identidade**. Vínculos, personas e módulos habilitados vêm do
`GET /api/me/context` (specs 04/05).

## CLI

Como na Central, um comando pra criar usuário fora de fluxo (bootstrap do primeiro
`platform_admin`): `python -m src.modules.auth.cli create-user --email … --name …` (pede
senha via prompt). O vínculo com a organização plataforma é dado pela spec 03/04.

## Critérios de aceite

1. `POST /auth/login` com credenciais válidas seta cookie httpOnly e `GET /auth/me` passa a
   responder a identidade; com credenciais inválidas, 401 e nenhum cookie.
2. `GET /auth/me` sem cookie responde 401.
3. Senha nunca aparece em log nem em resposta; `password_hash` é Argon2id.
4. O token de sessão não contém papel nem organização.
5. Trocar `PasswordAuthenticator` por outra implementação de `Authenticator` não exige
   mudança fora do módulo `auth`.
6. `current_user` é importável de `core` e usável por qualquer módulo sem importar `auth`.
