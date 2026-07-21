# 07 — Telas da frota

**Estado:** ✅ implementada (2026-07-21) — 138 testes de frontend (61 + 77),
`typecheck`/`lint`/`build` limpos. **Nenhum critério de fluxo foi observado em browser** — ver
`Como ficou`, que separa o que tem teste do que ficou por inspeção visual.
**Depende de:** `backend/10-frota.md` (as 14 rotas e as sete capabilities — está inteiro e
observável por requisição), `frontend/04-casca-e-personas.md` (a casca, o `Can`, o `ModuleGuard`),
`frontend/02-design-system.md` (os tokens).
**Entrega:** as telas do primeiro app de negócio — viagens, veículos, condutores e o relatório de
quilometragem — substituindo a rota-placeholder `/organizacoes/[orgId]/frota`.

## Objetivo

Aposentar a folha de papel presa na portaria, que é o que a `backend/10` prometeu e não pôde
cumprir sozinha: hoje o módulo tem schema, rotas e capabilities, e **nenhuma pessoa consegue
usá-lo sem `curl`**. Esta spec dá tela às três perguntas que o backend já responde — onde está
cada carro, quem rodou o quê, e quantos quilômetros cada veículo andou.

## Fora de escopo

- **Testes de componente.** Continuam sendo dívida com spec própria, e esta entrega a **agrava**
  de propósito: são quatro telas com formulário, filtro e estado. Decisão do Kauan em 2026-07-20,
  com o motivo dito na cara — tela que ninguém usa não tem regressão pra pegar, e a frota não tem
  nem tela. Ver a nota no fim.
- **CI.** Mesma decisão, mesma data. Segue pendurada na allowlist do `alembic check` que a `10`
  documentou.
- **Combustível, manutenção, multas, alerta de CNH, reserva e telemetria.** A `backend/10` os pôs
  fora de escopo e não há rota pra eles; uma tela não inventa domínio.
- **Pré-preencher o hodômetro inicial com a última leitura do veículo.** É a ergonomia mais óbvia
  que **não** dá pra fazer honestamente hoje: `VehicleResponse` tem `initial_odometer` (o do
  cadastro, que envelhece na primeira viagem) e não um `current_odometer`. Derivá-lo no frontend
  a partir de `GET /usos?veiculo={id}` seria uma segunda contabilidade de quilometragem vivendo na
  tela — exatamente a dívida que a `backend/08` registrou com o `effective_status` escrito duas
  vezes, e que não vamos repetir de olhos abertos. O campo é do backend e é **spec própria**.
- **Exportar o relatório (CSV/PDF).** Vai ser pedido no primeiro mês; é rota nova (`Accept` ou
  `/relatorios/quilometragem.csv`) e decisão de backend.
- **Editar veículo/condutor em massa, e apagar qualquer um dos dois.** Não existe `DELETE` no
  backend, e isso é decisão da `10` (o histórico é o produto). A tela oferece `PATCH status` —
  "Desativar" —, nunca uma lixeira.

## As telas ficam sob a rota que a casca já conhece

```
/organizacoes/[orgId]/frota              → Viagens   (a home do módulo)
/organizacoes/[orgId]/frota/veiculos     → Veículos
/organizacoes/[orgId]/frota/condutores   → Condutores
/organizacoes/[orgId]/frota/relatorios   → Quilometragem
```

**Um item no menu da casca, quatro telas dentro.** O `buildNav` monta **um** item por módulo
(`ModuleNav.path`, hoje `/frota`), e não vamos mexer nisso pra encaixar quatro: a casca é do
kernel, e um módulo que precisa editar o menu da casca pra existir quebra a promessa de que
módulo pluga sem tocar o núcleo. A navegação interna é do módulo, em abas no topo da tela — o
mesmo raciocínio que fez as capabilities morarem no descritor.

**A home do módulo é Viagens, não um dashboard.** É a única das quatro que um `collaborator`
enxerga com conteúdo: ele tem `vehicles.read` e `usages.write_own`, e nada mais. Um dashboard com
três cartões vazios seria a primeira coisa que a maior persona do produto veria.

O `ModuleGuard` da rota-placeholder atual **permanece** nas quatro — quem não contratou `frota`
não passa, e quem tenta a rota na mão leva 403 do `require_module`.

## Quem vê o quê é decidido por capability, nunca por persona

A tabela do backend, que é a fonte:

| Capability              | `company_admin` | `manager` | `collaborator` |
| ----------------------- | :-------------: | :-------: | :------------: |
| `frota.vehicles.read`   |       ✅        |    ✅     |       ✅       |
| `frota.vehicles.write`  |       ✅        |    ✅     |       —        |
| `frota.drivers.read`    |       ✅        |    ✅     |       —        |
| `frota.drivers.write`   |       ✅        |    ✅     |       —        |
| `frota.usages.read`     |       ✅        |    ✅     |       —        |
| `frota.usages.write`    |       ✅        |    ✅     |       —        |
| `frota.usages.write_own`|       ✅        |    ✅     |       ✅       |

Toda diferença de tela sai daí, via `<Can permission="frota.…">`, e **nenhuma sai de
`persona`**. Motivo: `company_admin` e `manager` recebem grants idênticos da frota e são personas
diferentes, enquanto o que separa o `collaborator` é capability. Ramificar por persona acertaria
por acidente hoje e erraria no primeiro papel novo. Vale a regra do `Can`: esconder é ergonomia,
o guard é do backend.

As abas seguem a mesma regra — **Condutores** e **Quilometragem** só aparecem com
`frota.drivers.read` e `frota.usages.read`. Um `collaborator` vê duas abas, e as duas funcionam.

## Viagens — a tela que carrega o módulo

`GET /usos` é **a única rota do módulo sem `require_permission`**: ela exige só o entitlement, e a
capability decide o *escopo do que volta*. Quem tem `usages.read` recebe a Empresa inteira; quem
não tem recebe só as viagens do próprio condutor (e lista vazia se não houver `drivers.user_id`
apontando pra ele). **A tela não implementa isso — ela confia.** Não há filtro "só as minhas" no
cliente: a lista já vem escopada, e um segundo filtro aqui seria uma regra de autorização escrita
no frontend.

Isso tem uma consequência que a tela precisa dizer em voz alta: um `collaborator` sem condutor
vinculado vê **lista vazia**, e vazio-por-escopo não é vazio-por-falta-de-dado. O estado vazio
dessa tela, sem `usages.read`, diz que talvez ninguém tenha vinculado seu cadastro de condutor, e
a quem pedir — senão a pessoa conclui que o sistema perdeu as viagens dela.

**Filtros vivem na URL** (`?veiculo=&condutor=&de=&ate=&abertos=`), não em estado de componente,
com os mesmos nomes que o backend usa. Uma lista filtrada é compartilhável e sobrevive ao F5 —
a mesma razão pela qual a organização ativa é o `orgId` do path e não uma store.

A coluna **Distância** vem do campo `distance` da resposta e é `null` na viagem aberta. **Nunca
calcule `end_odometer - start_odometer` na tela**, mesmo sendo trivial: o backend já o faz, e a
segunda conta é a que vai divergir no dia em que a regra ganhar um caso (troca de veículo no meio,
correção de leitura). Viagem aberta mostra "Em curso", não "0 km".

## Lançar viagem é um formulário de datas digitadas

**Retroativo é o caso normal** (`backend/10`), e a tela não pode sugerir o contrário: não existe
botão "Iniciar agora". `started_at` e `ended_at` são campos de data e hora, com o agora só como
valor **inicial** do campo — editável, e sem nenhum "usar horário atual" em destaque.

O formulário é **um só** pra viagem aberta e fechada: `ended_at` e `end_odometer` ficam num par
opcional. Deixar os dois vazios lança uma viagem em curso; preencher os dois já a lança encerrada,
que é o caso do lançamento retroativo de ontem. O par é indivisível — a tela exige os dois ou
nenhum, porque o `ck_vehicle_usages_closed_together` exige, e um 422 do banco por meio par é um
erro que a tela sabia evitar.

**`driver_id` é o campo que muda por capability**, e é o único:

- com `frota.drivers.read` — select de condutores ativos (`GET /condutores?status=active`);
- sem ela — **campo nenhum**. Omitir `driver_id` já significa "sou eu" (`backend/10`), e apontar
  outro condutor responde 403. Renderizar um select que a pessoa não pode preencher, ou um campo
  travado com o próprio nome, seria pedir 403 de propósito.

O select de veículos usa `GET /veiculos?status=active` — veículo inativo "some da escolha na tela,
não do sistema", como o docstring da rota já dizia, e é esta a tela de que ele falava.

**Encerrar viagem é ação própria, não edição.** `POST /usos/{id}/encerrar` existe porque os dois
campos vão juntos; a tela oferece "Encerrar" na linha da viagem aberta, com um diálogo de dois
campos. Deixar isso cair no `PATCH` genérico devolveria ao usuário a chance de encerrar pela
metade.

## Os erros que a tela traduz, e por quê cada um

O backend distingue estes casos e a tela não pode achatá-los em "erro ao salvar":

| Resposta | Quando                                           | O que a tela diz                                                                  |
| -------- | ------------------------------------------------ | --------------------------------------------------------------------------------- |
| **409**  | período sobreposto no mesmo veículo               | "Este veículo já tem uma viagem nesse período." — e é a mensagem mais importante da spec |
| **422**  | `started_at` no futuro                           | erro no campo de data, não um toast                                                 |
| **422**  | veículo ou condutor inativo                       | erro no select correspondente                                                       |
| **403**  | `write_own` apontando outro condutor              | não deve acontecer pela tela (o campo não existe); se acontecer, é bug e aparece    |
| **409**  | placa duplicada                                   | erro no campo placa                                                                 |

O 409 de sobreposição merece cuidado porque é o único que fala de um dado que **não está na tela**:
a viagem que colide é de outra pessoa, possivelmente de outro dia. A mensagem nomeia o veículo e o
período que o usuário tentou, pra ele conseguir procurar — e a tela oferece o atalho de filtrar as
viagens daquele veículo naquele intervalo (`?veiculo=…&de=…&ate=…`), que é exatamente a URL que a
seção de filtros já sabe montar. Sem isso, o usuário fica com um "não pode" sem saber por quê.

## Veículos, Condutores e Quilometragem

**Veículos** — lista paginada com filtro de status, formulário de cadastro/edição
(`plate`, `brand`, `model`, `model_year?`, `initial_odometer`) e **"Desativar"** em vez de apagar.
`initial_odometer` só é editável no cadastro: mudá-lo depois reescreve o passado de um veículo que
já rodou, e a tela não oferece o que o domínio não quer. (O backend aceita — é `PATCH` — e essa
diferença fica registrada aqui em vez de virar um `if` escondido.)

**Condutores** — mesma forma. O campo que merece nota é `user_id`: é o vínculo opcional com quem
tem login, e é ele que faz o `write_own` funcionar. Na tela é um select de membros da organização
(`GET /api/organizacoes/{orgId}/membros`, que é `members.read`) com um "— sem vínculo —" bem
visível, porque **o motorista terceirizado é caso de primeira classe**: ele dirige e nunca loga.
`license_expires_at` é dado e só dado — a tela mostra a data, e **não** pinta vencimento, porque
alerta de CNH está fora de escopo na `backend/10` e uma tarja vermelha aqui seria meia
implementação de compliance.

Se quem abre a tela não tem `members.read`, o select degrada pra "sem vínculo" e um aviso — não
quebra. `manager` tem `drivers.write` e pode não ter `members.read`; são mapas diferentes
(`PERMISSIONS_BY_ROLE` × o `grants` do módulo) e nada os obriga a concordar.

**Quilometragem** — `GET /relatorios/quilometragem` exige `de` e `ate` (obrigatórios na rota) e
aceita `agrupar_por=vehicle|driver`. A tela abre com o **mês corrente** e um seletor de período;
os dois parâmetros vão pra URL. Cada grupo mostra `total_km`, `closed_usages` e `open_usages` —
e **`open_usages` aparece sempre, mesmo zero**, porque é a nota de rodapé que explica por que o
total não bate com o que a pessoa esperava: viagem aberta não entra como zero km, entra como
contagem à parte.

## O descritor da frota sai do catálogo e vai pro módulo

`features/context/modules.ts` diz de si mesmo que "é provisório e some", e que cada módulo trará o
seu de `features/<módulo>/module.ts` quando existir. **A frota existe agora**, e faz no frontend o
mesmo movimento que a `backend/10` fez com `src/api/modules.py`: nasce `features/frota/module.ts`
com `key`, `label`, `path`, `personas` e `icon`, e o `MODULE_CATALOG` passa a compô-lo em vez de
declará-lo. `refeicoes` fica lá, sozinha, até a fase 2 — e o catálogo continua existindo, porque
alguém tem de montar a lista.

Nada mais da casca muda. A feature nova é `features/frota/` (api, schemas zod, hooks de query e
componentes), e ela importa `context` (o `Can`, o `orgId`) como as outras já importam.

## Critérios de aceite

1. Um `manager` numa Empresa com `frota` contratada abre `/organizacoes/{orgId}/frota`, vê as
   quatro abas, lança uma viagem retroativa (data de ontem, com `ended_at` e `end_odometer`
   preenchidos) e ela aparece na lista com a distância calculada.
2. Lançar uma segunda viagem no **mesmo veículo** com período sobreposto mostra a mensagem de
   conflito nomeando veículo e período — não um erro genérico — e oferece o atalho pra filtrar
   as viagens daquele veículo no intervalo.
3. Um `collaborator` na mesma Empresa abre a mesma URL e vê **duas** abas (Viagens e Veículos);
   `/frota/condutores` e `/frota/relatorios` não têm link pra ele.
4. O formulário de viagem do `collaborator` **não tem campo de condutor**, e a viagem que ele
   lança aparece com ele como condutor — provando que omitir `driver_id` resolveu pra si mesmo.
5. Um `collaborator` **sem** `drivers.user_id` apontando pra ele vê a lista de viagens vazia com o
   texto que explica o vínculo faltando, e não um "nenhuma viagem registrada".
6. Uma viagem aberta mostra "Em curso" na coluna de distância e um botão "Encerrar"; o diálogo
   exige `ended_at` **e** `end_odometer` juntos, e depois de encerrar a linha mostra os km.
7. Filtrar a lista por veículo e período muda a URL; abrir essa URL noutra aba reproduz a mesma
   lista filtrada.
8. Cadastrar veículo com placa já usada mostra o erro **no campo placa**; um veículo desativado
   some do select de lançamento e continua na lista de veículos com o status.
9. O relatório abre no mês corrente, agrupa por veículo, e trocar pra "por condutor" recarrega os
   grupos; um período com viagem aberta mostra a contagem de abertas separada do `total_km`.
10. Numa Empresa **sem** `frota` contratada, as quatro rotas caem no `ModuleGuard` e o item não
    aparece no menu.
11. `npm run typecheck` e `npm run lint` limpos; `npm run test` segue verde (os 61 atuais, mais o
    que for regra pura desta entrega — ver a nota abaixo).

## Nota sobre teste, escrita antes e não depois

Esta spec entrega quatro telas com formulário e **não** traz teste de componente, porque a infra
não existe e foi decidido em 2026-07-20 que ela vem depois das telas. O que dá pra provar sem DOM
**tem** de vir aqui, e é onde a dívida para de crescer sem rede: os schemas zod dos três
formulários, a tradução de erro (o mapa de 409/422/403 acima) e a montagem/leitura dos parâmetros
de filtro da URL são funções puras e ganham teste nesta entrega. O que fica descoberto é o que já
estava: submit, estado e redirect.

**Quem escrever a spec de teste de componente começa por aqui** — o formulário de viagem é o
maior cliente sem rede do projeto depois desta entrega, e o caso 2 (o 409 de sobreposição) é o
primeiro que eu escreveria.

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
de teste de componente da nota ¹ do `CLAUDE.md`, agravada de propósito por esta entrega e agora
com quatro telas de formulário esperando por ela.
