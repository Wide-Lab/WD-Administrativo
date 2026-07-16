# 01 — Fundação do frontend

**Estado:** ✅ implementada (`ef453e7`, 2026-07-16). Ver `Como ficou` no fim.
**Depende de:** nada. É a primeira spec de frontend a ser implementada.
**Entrega:** um projeto Next que sobe, tipa, linta e builda, com uma rota `/` vazia e o
provider de dados montado.

## Objetivo

Montar o esqueleto do frontend do superapp mantendo as convenções da casa (TypeScript
strict, Tailwind v4, shadcn, TanStack Query, zod, estrutura por feature, alias `#/*`), com a
diferença registrada na `00-visao-geral.md`: **roteamento é do Next (App Router)**, não
TanStack Router. O Next é **só frontend** — consome a API FastAPI, nunca usa route handlers
como backend.

## Fora de escopo

Qualquer estilo, componente de domínio, dado ou persona. Esta spec entrega uma página em
branco com o provider de dados montado. Tokens e tema são da `02`; login é da `03`; a casca,
os route groups por persona (`(admin)`, `(parceiro)`, `(colaborador)`) e a navegação são da
`04`. **Não crie os route groups aqui** — só o layout raiz e uma página placeholder.

## Stack

| Papel | Escolha |
|---|---|
| Framework | Next 15 (App Router) |
| UI | React 19 + TypeScript (`strict: true`) |
| Dados | TanStack Query v5 (client-side) |
| Estilo | Tailwind v4 via `@tailwindcss/postcss` |
| Componentes | shadcn/ui sobre Radix |
| Ícones | `lucide-react` |
| Validação | `zod` (tipos sempre `z.infer`, nunca à mão) |
| Testes | Vitest (só lib puras, sem DOM) |
| Qualidade | ESLint + Prettier |

Gerenciador de pacotes: **npm**. Node >= 20.

### Dependências

```
next react react-dom
@tanstack/react-query
zod
tailwindcss @tailwindcss/postcss
lucide-react clsx tailwind-merge class-variance-authority
```

Dev:

```
typescript
vitest
eslint prettier eslint-config-next
@types/react @types/react-dom @types/node
```

## Estrutura de pastas

```
frontend/
  src/
    app/
      layout.tsx           # <html>, providers, importa styles.css
      page.tsx             # placeholder vazio — conteúdo real chega nas specs 03+
      providers.tsx        # 'use client' — QueryClientProvider
    components/
      ui/                  # só shadcn: button, input, skeleton…
      layout/              # casca da página (app-shell, masthead) — preenchida na spec 04
    features/
      <domínio>/
        schema.ts          # zod
        types.ts           # z.infer, nunca escrito à mão
        api.ts             # cliente de dados do domínio
        use-<algo>.ts      # hooks TanStack Query
        lib/               # funções puras testadas
        components/         # componentes de domínio moram aqui, nunca soltos em components/
    lib/
      utils.ts             # cn()
    styles.css             # @import "tailwindcss"
  public/
  next.config.ts
  postcss.config.mjs
  tsconfig.json
  package.json
```

Regra: **componente de domínio mora em `features/<domínio>/components`.** `components/ui` é
só shadcn; `components/layout` é só casca da página.

## Alias de import

`#/*` aponta para `./src/*`, como na Central. O Next resolve via `tsconfig.json` (não precisa
do campo `imports` do `package.json`):

```json
{ "compilerOptions": { "paths": { "#/*": ["./src/*"] } } }
```

## Provider de dados

`src/app/providers.tsx` é um client component que monta `<QueryClientProvider>` com um
`QueryClient` estável (criado uma vez com `useState`). `src/app/layout.tsx` embrulha
`children` nesse provider. Dados de domínio são buscados **client-side** com TanStack Query,
contra `/api/*` — decisões de fetch em Server Component ficam por feature nas specs seguintes,
não são padrão global aqui.

## Contrato com o backend

O frontend sempre chama caminhos relativos `/api/*`. Em produção o nginx roteia `/api/*` pro
FastAPI; em dev, um rewrite do Next faz o mesmo:

```ts
// next.config.ts
import type { NextConfig } from 'next'

const config: NextConfig = {
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${process.env.API_URL}/api/:path*` }]
  },
}

export default config
```

`API_URL` aponta pro backend local (`http://localhost:8000`) em dev, via `.env`. Nenhum
componente conhece a URL do backend — só `/api/*`.

## Scripts

```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "typecheck": "tsc --noEmit",
  "test": "vitest run",
  "lint": "next lint",
  "format": "prettier --write . && eslint --fix .",
  "check": "prettier --check ."
}
```

## Critérios de aceite

1. `npm run dev` sobe em `http://localhost:3000` e a rota `/` renderiza sem erro no console.
2. `npm run typecheck` passa com `strict: true`.
3. `npm run build` builda sem warning de tipo.
4. `npm run check` e `npm run lint` passam num checkout limpo.
5. Um import `#/lib/utils` resolve tanto no editor quanto no build.
6. O `QueryClientProvider` está montado no layout raiz e um hook TanStack Query pode ser
   usado em qualquer client component sem erro de contexto.
7. Uma chamada a `/api/health` a partir do frontend em dev chega no backend via rewrite
   (com o backend da `backend/01-fundacao.md` no ar).

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
