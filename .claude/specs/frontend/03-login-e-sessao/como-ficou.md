# 03 — Login e sessão — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

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
