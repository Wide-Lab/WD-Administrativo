# 01 — Fundação do frontend — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Todos os critérios batem. Diferenças:

- **`zod` está na v3**, não na v4 — a spec não fixou major, e a v3 é o que a casa usa. A regra
  que importa (tipos sempre `z.infer`, nunca à mão) vale igual.
- **A `/` placeholder da spec durou até a `03`**: hoje é a área autenticada de exemplo
  (identidade + sair), ainda placeholder — quem decide a home de verdade é a `04`.
- **Os route groups por persona seguem não existindo**, como esta spec mandou. Continuam sendo
  da `04`.
- `components/layout/` recebeu só o `wordmark.tsx` (usado pelo login da `03`); a casca de
  verdade é da `04`.
- Tooling como especificado: Vitest sem DOM (só libs puras), ESLint + Prettier, alias `#/*`,
  rewrite `/api/*` → `API_URL`. O `Dockerfile` e o `nginx/default.conf` fecham o mesmo contrato
  em prod.
