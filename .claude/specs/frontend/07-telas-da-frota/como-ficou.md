# 07 — Telas da frota — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

As quatro telas existem, a frota saiu do `curl` e a suíte foi de **61 para 138 testes**, com
`typecheck`, `lint` e `build` limpos. O descritor saiu do catálogo pra `features/frota/module.ts`,
como a spec pedia, e em `features/context/` **só** o `modules.ts` mudou — a casca não foi tocada.

### A spec errou o nome dos valores de `agrupar_por`, e o código venceu

A spec diz `agrupar_por=vehicle|driver`. O enum é `MileageGroupBy` em
`frota/domain/rules.py:51`, e os valores são **`veiculo`/`condutor`**. A tela seguiu o código, com
o desvio anotado no `schema.ts`. Fica registrado aqui em vez de corrigido no corpo acima porque é
exatamente o tipo de erro que uma spec escrita antes do consumo produz — e o remédio é o que esta
entrega já fez: ler o backend antes de escrever a tela, e não confiar na spec para nomes.

### `ate` é expandido pra o fim do dia, e sem isso a data mentiria

O backend filtra `started_at <= ate`. Uma data pura é meia-noite, então `ate=2026-07-20`
esconderia **todas** as viagens do próprio dia 20 — o usuário pediria "até hoje" e não veria hoje.
A tela expande pra `T23:59:59.999`, com teste. Vale pro filtro de viagens e pro relatório.

**A expansão estava certa e o fuso estava errado** — ver a seção do fuso, abaixo.

### O instante ia sem fuso, e isso estava errado (corrigido em 2026-07-22)

**Esta entrega decidiu mandar o instante digitado sem fuso, e a decisão era errada.** Está aqui
porque foi escrita como escolha justificada, no `startOfDay`/`endOfDay` de `lib/filters.ts`: _"sem
fuso na string, de propósito: o backend interpreta o horário como o dele, e carimbar um `Z` aqui
deslocaria o recorte"_. A premissa é que "o dele" fosse o fuso de quem lê a tela. Não é: o
container roda em UTC.

Apareceu como **500 no "Lançar Viagem"** — o `started_at` ingênuo chegava até `is_future` e batia
contra um `now()` aware, que o Python recusa comparar. Mas o crash foi o sintoma barato. O caro era
o filtro de período, onde nada explodia: o Postgres coagia o ingênuo pra UTC calado, e "até 20/07
23:59" virava 20:59 em São Paulo, escondendo as viagens do fim da tarde **sem erro nenhum**. Foi a
tela dizendo que não havia lançamento onde havia — exatamente o que a seção do `ate`, acima, existia
pra evitar.

O conserto, nas duas pontas:

- **Backend** — os instantes de entrada da frota viraram `AwareDatetime` (`started_at`/`ended_at`
  de criar, editar e encerrar; `de`/`ate` do `GET /usos` e do relatório). Instante sem fuso é
  **422**, não 500 e não suposição: o servidor não tem como saber onde a viagem foi digitada, e
  normalizar pra UTC teria trocado o erro barulhento por dado três horas fora do lugar. `is_future`
  continua pura — quem garante o fuso é a borda.
- **Frontend** — `features/frota/lib/instants.ts` (`toInstant`/`toInstantOrUndefined`) carimba o
  offset de quem digitou. `new Date(local)` sobre string **sem** offset é hora local, que é o certo
  aqui e o oposto do que `isoDatePart` e `formatMoment` querem, onde a mesma string é só texto a
  recortar — os três casos convivem e a distinção está nos docstrings.

Os testes novos afirmam **equivalência de instante**, nunca string literal (`new Date(2026, 6, 20,
8, 30).toISOString()`), senão passariam só no fuso de quem rodou a suíte. Do lado do backend, dois
testes prendem o 422 no lançar e no encerrar, e o docstring de um deles nomeia a alternativa
tentadora — "normalizar assumindo UTC" — pra que a regressão não volte como conserto.

**A frota é o único lugar do sistema com entrada de data-hora**: no `access` todo `datetime` de
schema é resposta, e o único `type="date"` fora daqui é `license_expires_at`, que é `date` puro e
não tem fuso pra errar. O bug estava contido, e o `instants.ts` mora em `features/frota/lib` por
isso — quando Refeições tiver campo de data-hora, ele sobe pra `src/lib`.

### A tradução do 409 casa por texto, e isso é dívida de backend

O `core` devolve `code: "conflict"` para os **cinco** conflitos distintos de `vehicle_usages`, e a
sobreposição de período precisa de mensagem própria — é o único erro que fala de um dado que não
está na tela. Sem um código por constraint, a prosa é o único discriminador. Ficou contido num
arquivo só (`lib/frota-error.ts`), preso por testes que usam as **strings literais** do backend:
reescrever a mensagem lá quebra teste aqui, que é o mínimo que se pode fazer para um acoplamento
que não deveria existir. O conserto é `code` por constraint, e é spec de backend.

### O que a tela **não** revalida, de propósito

Só três regras vivem no cliente: o par indivisível (`ended_at` + `end_odometer`), os campos
obrigatórios e a data futura — esta última porque é a única que o banco **não** consegue impor (um
`CHECK` com `now()` é impossível no Postgres, como a `backend/10` registra). `ck_vehicle_usages_period`
e `_odometer` **não** foram reimplementados: seriam a segunda contabilidade que esta spec manda
evitar. Eles chegam como 409 e são roteados pro campo certo.

### O quarto furo de backend: **membro não tem nome nem e-mail**

A spec pede, pro `drivers.user_id`, "um select de membros da organização". A `MemberResponse`
(`access/adapters/http/schemas.py`) devolve `id`, `user_id`, `organization_id`, `role`, `status`,
`created_at` — **nenhuma identidade** —, e não há rota que traduza `user_id` em pessoa. O select
mostra `papel · <8 primeiros caracteres do uuid>`, que é ruim de usar e está anotado no código
como lacuna do backend, não escolha da tela.

Este achado é **o mesmo** que a `frontend/08` encontrou pelo outro lado (as colunas da lista de
membros), nas duas implementações rodando em paralelo e sem contato. Duas telas independentes
esbarrando na mesma ausência é o que o torna spec de backend e não contorno local:
`MemberResponse` precisa de `name`/`email`, ou o kernel precisa de uma rota de diretório.

### Os primitivos novos usam os tokens do projeto, não o output stock do shadcn

`table.tsx`, `select.tsx`, `dialog.tsx` e `textarea.tsx`. O output padrão do shadcn referencia
`bg-background`, `text-muted-foreground` e `border-input`, que **não existem** neste tema — e
utilidade inexistente não é cor neutra, é ausência de estilo. Foram espelhados nos primitivos que
já existiam. `select.tsx` é `<select>` nativo (sem dependência nova); `dialog.tsx` é Radix, e é a
**única dependência que esta entrega adicionou** (`@radix-ui/react-dialog`), pelo focus trap,
`Escape` e `aria-modal` dos dois diálogos de viagem.

### Filtro de viagem na URL; filtro de status de veículo/condutor, não

A spec põe os filtros na URL e a razão é o atalho do 409 de sobreposição, que precisa montar um
link. Isso vale pra **viagens**. Os filtros de status de veículo e condutor ficaram em estado
local: ninguém precisa compartilhar "a lista de veículos inativos", e subir tudo pra URL por
simetria seria cerimônia sem cliente.

### O que tem teste, e o que não tem

**77 testes novos**, em `schema.test.ts` (os três formulários, com o par indivisível e a data
futura), `lib/frota-error.test.ts` (o mapa 409/422/403, com as strings literais do backend) e
`lib/filters.test.ts` (ida e volta: a URL que a tela escreve é a que ela sabe ler, sobre quatro
formatos de filtro, mais os casos de mês corrente, mês de 30 dias, fevereiro bissexto e
`agrupar_por` inválido).

**O que não tem teste, e não foi observado:** os critérios 1–10 descrevem interação com quatro
personas diferentes. A stack não foi subida nesta sessão; as telas estão implementadas contra os
contratos lidos no código do backend e verificadas por build, **não** vistas rodando. É a dívida
de teste de componente que as `04`–`06` registraram e que a `00-visao-geral.md` acompanha em
`Fases`, agravada de propósito por esta entrega e agora com quatro telas de formulário
esperando por ela.
