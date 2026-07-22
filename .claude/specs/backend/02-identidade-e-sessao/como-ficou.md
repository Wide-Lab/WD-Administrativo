# 02 — Identidade e sessão — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

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
