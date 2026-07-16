# 05 — Seleção de organização

**Estado:** ✅ implementada (2026-07-16). Ver `Como ficou` no fim — em especial a ordem de
precedência do redirect, que **muda uma decisão da `04`**, e quem observou cada critério.
**Depende de:** `frontend/04-casca-e-personas.md`, `backend/03-organizacoes-e-tenancy.md`.
**Entrega:** a troca de organização ativa quando um usuário pertence a mais de uma —
o Parceiro que atende N Empresas, ou a pessoa que é Colaborador aqui e admin ali.

## Objetivo

O backend escopa tudo pela organização do path `/api/organizacoes/{orgId}/...` (backend spec
03). No frontend, a organização ativa **é o `orgId` da URL** — trocar de organização é
navegar. Esta spec cobre como o usuário escolhe e troca esse `orgId`, sem novo login.

## Fora de escopo

Provisionamento de organização (é do `platform_admin`, backend spec 03) e associação por
convênio (spec 06). Aqui só se **escolhe entre** organizações onde o usuário já tem vínculo.

## Organização ativa = URL

- A org ativa é o `orgId` do path — nenhum header, nenhum store de "org ativa". O cliente de
  fetch **não** injeta `X-Organization-Id`; as chamadas já vão pra `/api/organizacoes/{orgId}/...`.
- Trocar de organização é **navegar** pra `/organizacoes/{outroId}/...`. Como o `orgId` das
  queries muda, o TanStack Query naturalmente troca o cache por org (chaves incluem `orgId`) —
  não há dado da org anterior servido pra outra. A persona pode mudar na troca (Colaborador
  numa Empresa → admin num Parceiro); o `layout.tsx` de `/organizacoes/[orgId]` re-resolve.
- Um `localStorage` guarda só o **último `orgId` visitado**, usado apenas pra decidir pra
  onde redirecionar logo após o login.

## Resolução inicial (pós-login)

Como não há org na URL logo após `/entrar`, um passo decide o redirect:

- 0 vínculos → tela "sem acesso" (raro; conta sem membership).
- 1 vínculo → redireciona direto pra `/organizacoes/{orgId}`, **sem** seletor.
- 2+ vínculos → usa o último `orgId` do `localStorage` se ainda for um vínculo válido; senão,
  o primeiro vínculo. O seletor (abaixo) permite trocar depois.

## Seletor (UI)

Um controle no masthead da casca (só aparece com 2+ vínculos), alimentado por `memberships`
de `GET /api/me/contexto`: lista as organizações do usuário com tipo e nome (ex.: "Widelab —
Colaborador", "Restaurante Gomes — Parceiro"), marca a org do `orgId` atual, e ao selecionar
**navega** pra `/organizacoes/{outroId}`. Em telas de Parceiro que atende muitas Empresas, o
mesmo padrão vale pra filtrar "por Empresa" dentro da persona Parceiro, mas isso é refinamento
dos módulos, não desta spec.

## Critérios de aceite

1. Usuário com um vínculo nunca vê o seletor; com dois ou mais, vê e consegue trocar.
2. Trocar de organização navega pra `/organizacoes/{outroId}`, re-resolve a persona, e nenhuma
   query continua servindo dado da organização anterior (chave de cache inclui `orgId`).
3. Nenhuma chamada envia `X-Organization-Id`; a org viaja no path da URL.
4. O último `orgId` visitado persiste e orienta o redirect pós-login; se o vínculo deixar de
   existir, cai no primeiro vínculo sem quebrar.
5. Navegar pra um `orgId` sem vínculo (403 do backend) leva à reseleção, não a uma tela
   quebrada.

## Como ficou

Os cinco critérios batem, mas **a verificação foi dividida** — e é a mesma divisão que a `04`
registrou, pelo mesmo motivo (não há testing-library no projeto, e eu não tinha browser).
O que **eu** observei rodando: o critério **4** pelos testes puros de `homePathFor` (`npm run
test`, 36 testes — os 31 da `04` mais 5), o **3** por inspeção estrutural com prova de que ela é
suficiente (abaixo), e o
contrato de que os **1**, **2** e **5** dependem por `curl` contra a stack real. O que ficou pro
**Kauan observar no browser**: o seletor aparecendo/sumindo (**1**), a troca re-resolvendo a
persona (**2**) e o 403 caindo em reseleção (**5**).

O caso de teste ficou bom o bastante pra merecer registro: `sel05@acme.com.br` é `collaborator`
na Acme **e** `partner_admin` no Restaurante Gomes — o "Colaborador aqui e admin ali" da
`Entrega`, literal. Verificado por `curl`: o `/eu` devolve `persona: "collaborator"` +
`modules: ["refeicoes"]` numa, e `persona: "partner"` + `modules: []` na outra. As duas cascas
são **formas diferentes** (barra inferior mobile-first × barra lateral), então a troca prova o
re-resolve a olho nu. E a Widelab, onde ele não tem vínculo, responde **403** de verdade.

O que a implementação decidiu, e a spec não previa:

- **O último `orgId` ganha do atalho da Plataforma, e isso muda uma decisão da `04`.** A `04`
  fixou "vínculo de plataforma ganha da lista"; agora a ordem é **onde a pessoa estava** > mesa da
  Plataforma > primeiro vínculo. O critério 4 pede que o último `orgId` "oriente o redirect", e
  quem tem vínculo de plataforma *e* de tenant tem 2+ vínculos — a regra desta spec o alcança. É
  reversível pelo seletor, e não atropela quem só usa a mesa: **a `/plataforma` esquece o último
  `orgId`** (`forgetLastOrgId`), então quem trabalha lá nunca guarda nenhum e segue caindo lá.
  Sem esse esquecimento, um `platform_admin` que visitasse um tenant **uma vez** cairia nele pra
  sempre — o bug que a precedência criaria sozinha.
- **`homePathFor` recebe o `lastOrgId` por parâmetro; não lê o `localStorage`.** O Vitest deste
  projeto roda em `environment: 'node'` e só inclui `*.test.ts` — não há DOM. Ler o storage dentro
  da regra a tornaria improvável sem jsdom, que é justamente a dívida que a `04` registrou. Com o
  parâmetro, a regra (incluindo "vínculo lembrado que sumiu → primeiro vínculo", do critério 4)
  fica provada em teste puro, e o efeito colateral mora numa peça só, `lib/last-org.ts`.
- **`lib/last-org.ts` não tem teste, e é o resto da mesma dívida.** Ela engole toda falha de
  `localStorage` (não existe no SSR, e **lança** com armazenamento bloqueado — Safari privado,
  iframe), porque um palpite de rota não vale derrubar a casca. Sem storage, degrada pro primeiro
  vínculo. Nada disso está coberto.
- **O seletor mostra tipo *e* papel — a spec pedia "tipo e nome", mas exemplificava com papel.**
  Os exemplos do texto ("Widelab — Colaborador", "Restaurante Gomes — Parceiro") não são a mesma
  regra: o primeiro é papel, o segundo é tipo. Entraram os dois ("Empresa · Colaborador") porque
  cada um resolve metade: o tipo separa "Acme, a Empresa" de "Gomes, o Parceiro"; o papel separa
  os dois vínculos da `Entrega`, que numa lista só de tipos seriam **duas linhas idênticas**. O
  `ROLE_LABEL` é rótulo de exibição do valor que o backend mandou — **não** é papel→persona, que
  segue sendo decisão do `access` e o frontend não recalcula.
- **Um primitivo novo entrou no design system: `components/ui/dropdown-menu.tsx`** (+ a dependência
  `@radix-ui/react-dropdown-menu`). A `02` entregou cinco primitivos e parou; um seletor precisa de
  um controle de escolha. Radix e não `<div onClick>` porque o que ele traz não é aparência: foco
  preso, seta, `Esc`, colisão com a borda da janela e `aria-checked` no item ativo (`RadioItem`, que
  é o certo pra opções mutuamente exclusivas). Duas correções vieram de conferir o projeto em vez de
  colar o shadcn: as classes de animação (`animate-in`, `zoom-in-95`) seriam **no-op**, porque não
  há plugin de animação aqui — e `prefers-reduced-motion` já é global no `styles.css`, então
  `motion-safe:` seria redundante; e o item **não** leva `outline-none`, pra valer o anel de foco
  global que o `styles.css` chama de baseline.
- **O seletor entrou também no masthead da Plataforma, e é o que fecha o critério 1 pra ela.** A
  spec diz "masthead da casca", e a casca da Plataforma é outra (`platform-shell`). Sem ele, um
  `platform_admin` com vínculo num tenant veria o critério 1 falhar — era o que a `04` deixou
  anotado ("hoje a Plataforma alcança um tenant navegando pra `/organizacoes/{orgId}`", isto é,
  editando a URL). **Não** é a lista de tenants: essa continua fora de escopo, porque lista tenant
  que não é vínculo seu.
- **O critério 5 fecha por redirecionar pra home + seletor, não por uma tela de reseleção
  própria.** É a interpretação, e vale dizê-la: a `04` decidiu que 403 redireciona em vez de
  mostrar "acesso negado", porque o caso comum não é invasão — é URL velha ou link colado. O
  destino é uma organização real da pessoa, com o seletor no masthead; "reseleção" é isso, e não
  uma tela quebrada. **A org que negou nunca é lembrada**: só se lembra `orgId` que o backend
  deixou abrir, então ela não volta como destino do próximo login.
- **A `/` deixou de derivar a tela de "sem vínculo" do destino.** Antes, `home === null` era o
  mesmo que "não tem vínculo"; agora o destino depende do `localStorage`, que só pode ser lido no
  efeito (lê-lo na renderização daria hidratação divergente). A tela passou a perguntar o que
  realmente quer saber — `memberships.length === 0` —, e o destino ficou só no efeito.
- **O `/api/me/contexto` agora é buscado em toda página de organização, e antes não era.** O
  masthead precisa dos vínculos pra saber se há escolha, então `useCanSwitchOrganization` o chama
  sempre; antes, sob `/organizacoes/[orgId]`, ele só saía no 403. É uma requisição a mais por
  carga fria — cacheada por 30s e quase sempre já feita pela `/` — e é o preço de a regra "só
  aparece com 2+ vínculos" morar num lugar só.
- **Nada envia `X-Organization-Id`, e não foi preciso mudar nada pra isso** (critério 3). Não é
  vacuidade: `apiFetch` é o **único** ponto de fetch do frontend, e os únicos cabeçalhos que ele
  monta são `Content-Type` e o passthrough do chamador — não existe cabeçalho de organização em
  lugar nenhum do `src`. A org viaja no path porque `getOrgContext`/`getOrganization` a interpolam
  na URL. O seletor não guarda estado nenhum: ele **navega**, e é isso que mantém a organização
  ativa sendo a URL.
- **Sem teste de componente pro seletor** — a peça nova mais arriscada é a que não tem rede. É a
  mesma dívida da `04`, agora com mais um cliente: uma spec de infra de teste de componente
  (testing-library + jsdom) resolveria `nav`/`Can`/`ModuleGuard`/seletor de uma vez.
