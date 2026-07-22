# 09 — Console da Plataforma (tenants e módulos vendidos)

**Estado:** 📋 a implementar (escrita em 2026-07-20) — **bloqueada** por uma spec de backend ainda
não escrita: o primeiro admin no `POST /organizacoes`, decidido em 2026-07-21. Ver "A decisão que
destrava esta spec", no fim.
**Depende de:** `backend/03-organizacoes-e-tenancy/spec.md` (provisionar tenant),
`backend/05-modulos-e-entitlements/spec.md` (o catálogo e o entitlement),
`frontend/04-casca-e-personas/spec.md` (a `PlatformShell`, que já existe e está vazia).
**Entrega:** a área da Widelab como operadora — listar e provisionar tenants, e ligar/desligar
módulo por Empresa.

## Objetivo

Dar tela ao ato comercial que o produto inteiro promete: **vender um módulo é ligar um flag, sem
deploy**. Hoje o flag se liga por `PUT` no `curl` ou pela CLI, e a `/plataforma` é um card que
diz, textualmente, que "a lista de tenants e a gestão de entitlements ganham tela nas próximas
entregas". É esta entrega.

## Fora de escopo

- **Faturamento, contrato, plano e preço.** A plataforma sabe *o que* cada Empresa contratou, e
  não *por quanto*. Não há schema pra isso e inventá-lo aqui seria fazer produto pela tela.
- **Editar organização depois de criada.** Não existe `PATCH /organizacoes/{orgId}`. Nome e
  documento entram na criação e ficam; o `type` é **imutável por decisão** (`00-visao-geral.md`),
  e a ausência da rota é coerente com isso.
- **Desativar/excluir tenant.** Sem rota, e é assunto sério (o que acontece com os dados, com as
  sessões abertas, com os convênios do outro lado). Spec de backend.
- **Testes de componente e CI.** Adiados em 2026-07-20, como nas `07` e `08`.
- **Gerir pessoas de um tenant a partir daqui.** A Plataforma não convida — é decisão da
  `backend/08` ("convidar é ato da organização, não da Plataforma"), e ela tem consequência
  grave que esta spec **não** resolve. Ver o achado no fim, que é o mais importante deste
  documento.

## As telas ficam dentro da `/plataforma`, e isso é a decisão principal

```
/plataforma                        → Tenants (lista + provisionar)
/plataforma/organizacoes/[orgId]   → O tenant: dados e módulos contratados
```

A rota de módulos do backend é **escopada por organização**
(`/api/organizacoes/{orgId}/modulos`), então a tela precisa de um `orgId`. A tentação é montá-la
em `/organizacoes/[orgId]/modulos`, dentro da casca do tenant — e está errada por duas razões:

1. **É a tela de quem vende, não de quem usa.** O próprio backend diz isso: `modules.read` é de
   `platform_admin`, e "quem consome módulo não pergunta aqui — o `/me` já devolve as chaves
   habilitadas". Uma tela que nenhum membro do tenant pode abrir não pertence à navegação do
   tenant.
2. **A casca de `/organizacoes/[orgId]` resolve persona e monta o menu do tenant.** Um
   `platform_admin` inspecionando a Acme entraria na casca *da Acme* — que é justamente o que a
   `frontend/04` construiu pra quem é membro dela. A `PlatformShell` existe porque administrar
   tenants é o que se faz **antes** de haver tenant ativo.

Então o `orgId` aqui é **parâmetro do que se está inspecionando**, não organização ativa. Vale
uma consequência que passa despercebida e quebraria coisa entregue:

> **Abrir `/plataforma/organizacoes/{orgId}` não escreve o `lib/last-org.ts`.** O último `orgId`
> visitado decide o redirect pós-login (`frontend/05`), e ele significa "a organização onde eu
> estava trabalhando". Um `platform_admin` que inspecionou doze tenants numa tarde cairia, no
> login seguinte, dentro do décimo segundo cliente. A `/plataforma` já **esquece** o último
> `orgId` ao abrir, e as telas desta spec preservam esse comportamento.

## Tenants

`GET /organizacoes` (`organizations.read`, só `platform_admin`), paginado, com filtro por tipo
(`?tipo=company|partner`) que vai pra URL. Colunas: nome, tipo (`ORGANIZATION_TYPE_LABEL`),
documento e data de criação. A linha leva pro detalhe.

A organização `platform` aparece na lista — ela existe, é semeada na migration `0002`, e
escondê-la seria a tela mentindo sobre o que o banco tem. Ela não tem detalhe de módulos (não é
`company`), e o link leva a uma tela que diz isso.

**Provisionar** é `POST /organizacoes` com `type` (`company` ou `partner`), `name` e `document?`.
`platform` **não** é oferecido no select: "não se cria por aqui — é a Widelab como operadora,
semeada na migration". O select tem duas opções, e o motivo fica no código.

**O formulário tem um quarto campo, e ele depende de uma mudança de backend ainda não escrita:**
o e-mail do primeiro administrador. Ver "A decisão que destrava esta spec", no fim — a rota passa
a aceitar `admin_email` e a criar o convite na mesma transação. Enquanto essa spec de backend não
existir, **este campo não é implementável** e provisionar entrega uma Empresa vazia; a tela então
diz, no sucesso, que o primeiro acesso ainda sai pela CLI. É o único ponto desta spec que
depende de trabalho de fora dela.

## O tenant: dados e módulos

`GET /organizacoes/{orgId}/modulos` devolve **os habilitados mais o catálogo** do que dá pra
habilitar, numa resposta só. A tela é uma lista de todos os módulos do catálogo, cada um com um
switch:

| Ação             | Rota                                    | Nota                                        |
| ---------------- | --------------------------------------- | ------------------------------------------- |
| ligar            | `PUT .../modulos/{chave}`               | idempotente — 200 no que já estava ligado    |
| desligar         | `DELETE .../modulos/{chave}`            | idempotente — 204 no que já estava desligado |

Os dois serem idempotentes é o que deixa o switch ser **otimista** sem risco de estado
inconsistente: clicar duas vezes converge, e o refetch confirma. É raro poder fazer isso; aqui dá,
e vale dizer por quê em vez de só fazer.

Desligar tem confirmação, e ela **nomeia a consequência real**: "a partir daqui as rotas do
módulo voltam a responder 403". Não é destrutivo (o entitlement é linha, os dados do módulo
ficam), mas é imediato e visível pro cliente inteiro — e a diferença entre "some da vista" e
"apaga os dados" é exatamente o que uma confirmação vaga deixa a pessoa imaginar.

**Só `company` tem módulo.** Abrir o detalhe de um Parceiro mostra os dados e, no lugar da lista,
a explicação — não uma lista vazia, que sugeriria "ainda não contratou nada". Quem garante isso é
o banco (FK composta contra `organizations(id, type)`), e a tela concorda com ele em vez de
descobrir por 422.

O catálogo hoje traz `refeicoes` (sem código, `grants={}`) e `frota` (completa). **A tela não
distingue os dois, e é de propósito**: ligar `refeicoes` numa Empresa é legítimo — registra a
venda antes de o módulo existir, que é precisamente o que a `backend/05` desenhou. O que a pessoa
vê é o catálogo, não o estado de implementação.

## Critérios de aceite

1. Um `platform_admin` abre `/plataforma` e vê a lista de tenants paginada; filtrar por
   `?tipo=partner` muda a URL e a lista, e a URL reproduz o filtro noutra aba.
2. Quem **não** é `platform_admin` não alcança `/plataforma` (guard já entregue pela `04`) nem as
   telas desta spec.
3. Provisionar uma Empresa a faz aparecer na lista; o select de tipo oferece **duas** opções, sem
   `platform`.
4. Abrir o detalhe de uma Empresa mostra todos os módulos do catálogo com o estado atual; ligar
   `frota` e recarregar mantém ligado.
5. Depois de ligar `frota` pra uma Empresa, um membro dela vê o item "Frota" no menu **sem
   deploy** — é o critério que prova a promessa comercial de ponta a ponta, e ele atravessa as
   duas cascas.
6. Desligar `frota` pede confirmação nomeando o 403; depois disso, o item some do menu do membro e
   a rota do módulo responde 403.
7. Ligar um módulo já ligado (dois cliques rápidos, ou duas abas) converge sem erro na tela.
8. Abrir o detalhe de um Parceiro mostra a explicação de que módulo é de Empresa, não uma lista
   vazia.
9. Inspecionar tenants em `/plataforma/organizacoes/{orgId}` **não** muda o destino do próximo
   login: sair, entrar de novo e cair onde se estava antes, não no último tenant inspecionado.
10. `npm run typecheck` e `npm run lint` limpos.

## A decisão que destrava esta spec

**Uma Empresa recém-provisionada não tem como ganhar seu primeiro membro pelo produto.**

O caminho completo de vender é: criar a Empresa → ligar os módulos → e alguém de lá precisa
entrar. Esse terceiro passo **não existe em tela nenhuma**, e não é omissão desta spec:

- `platform_admin` **não tem** `invitations.write` — decisão explícita da `backend/08`, porque
  convidar é ato da organização;
- ele tem `members.write`, mas **não existe `POST /membros`** — criar vínculo é convite
  (`backend/06`), e `PATCH /membros/{id}` só edita o que já existe;
- e a organização nova não tem ninguém com `invitations.write` pra convidar o primeiro, porque
  ela não tem ninguém.

É um ovo-e-galinha real, e hoje só a CLI o quebra:
`python -m src.modules.access.cli grant --email … --role company_admin --org …`. O `CLAUDE.md`
afirma que depois da `backend/08` restou "**um caso só**" pra CLI — o bootstrap do primeiro
`platform_admin`. **São dois**: este é o outro, e ninguém tinha notado porque nenhuma tela chegou
perto de provisionar um tenant.

Havia três saídas, e o Kauan escolheu a segunda em **2026-07-21**:

| Saída                                                                     | Decisão                                                       |
| ------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `platform_admin` ganha `invitations.write` na org que acabou de criar      | ❌ contradiz a `backend/08` frontalmente                       |
| **`POST /organizacoes` aceita o e-mail do primeiro admin e cria o convite na mesma transação** | ✅ **escolhida**                       |
| aceitar que provisionar é ato de operação, e a CLI é o caminho             | ❌ deixaria o console entregando tenant morto                  |

**Por que a segunda ganha:** ela mantém de pé a decisão que a `backend/08` registrou — *convidar é
ato da organização, não da Plataforma* — em vez de abrir exceção nela. O convite não nasce de um
`platform_admin` exercendo `invitations.write`; nasce **da própria organização, no instante em que
ela nasce**, como parte do ato de existir. A capability continua não sendo da Plataforma, e não há
`if` de "só na org que ele acabou de criar" pra alguém afrouxar depois.

A transação única é o que faz valer: uma Empresa **nunca** existe sem caminho de entrada. É a
mesma forma que o auto-cadastro de Parceiro já tem (`backend/06`), onde organização, primeiro
`partner_admin` e vínculo nascem juntos ou não nascem — e ali a atomicidade é testada por
`TRUNCATE` entre testes, exatamente o padrão que esta rota vai herdar.

**Isso é spec de backend e ainda não foi escrita.** Ela é pequena (um campo opcional no request,
o `CreateInvitationUseCase` chamado dentro da mesma `uow`, e o e-mail saindo pelo
`EmailSender` que já existe) e tem uma pergunta em aberto que **não** é de frontend: se
`admin_email` é opcional ou obrigatório — obrigatório impede tenant órfão por construção, opcional
preserva o caso de provisionar antes de saber quem administra. Quem escrever decide.

Até lá, o critério 5 é observável só num tenant que já tenha membro, e o campo de e-mail do
formulário de provisionar não existe. **A `frontend/09` não deve ser implementada antes dessa
spec de backend** — não porque quebra, mas porque entregaria o console completo com o único
caminho que importa (vender e o cliente entrar) ainda passando por CLI.
