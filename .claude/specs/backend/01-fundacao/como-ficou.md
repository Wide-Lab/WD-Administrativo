# 01 — Fundação do backend — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Todos os critérios batem, com estas diferenças em relação ao texto acima — a **decisão** vale,
o **desenho de pastas** cedeu onde o código pediu:

- **`core/security.py` virou o pacote `core/security/`.** A spec previa dois arquivos
  (`passwords.py`, `jwt.py`); o real tem também `identity.py` (tipos `CurrentUser`/`UserId` e
  as portas `UserReader`/`Authenticator`), `session.py` (emitir/ler cookie, `current_user`) e
  `startup.py`. Cresceu na spec `02`, não aqui — a fundação entregou só os primitivos.
- **`core/database/` ganhou `session.py` e `ports.py`**, não previstos: `SessionDep` (a sessão
  por request, que todo adapter injeta) e as portas de persistência. Sem `SessionDep` cada
  módulo reinventaria o ciclo de vida da sessão.
- **`adapters/http/dependencies/` (pasta) virou dois arquivos irmãos**, `dependencies.py`
  (factories) + `types.py` (os `Annotated[...]`). Mesma separação, sem o nível de pasta a
  mais. **É este o formato a seguir nos módulos seguintes.**
- **Critério 4 ("`src/modules/` vazio") era verdade só até a spec `02`** — hoje mora ali o
  `auth`. O critério continua registrando a intenção original: a fundação não trouxe módulo
  nenhum junto.
- `core/types.py` e `core/pagination/` vieram do `seifert` como a spec mandou; `core/logging.py`
  e `core/exceptions.py` existem conforme descrito.
- O `docker-compose.yml` acabou entregando a **stack completa** (Postgres + backend + frontend
  + nginx, com rede `db-internal` isolada), não só o Postgres — a spec deixava isso pra
  "quando o frontend existir", e o frontend chegou junto.
