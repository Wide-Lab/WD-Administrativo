# 08 — Gestão da organização (pessoas, convites e convênios)

**Estado:** 📋 a implementar (escrita em 2026-07-20).
**Depende de:** `backend/04-membros-e-autorizacao.md` (membros e papéis),
`backend/08-gestao-de-convites.md` (listar e revogar convite — a spec que nomeou esta aqui),
`backend/03-organizacoes-e-tenancy.md` (convênios), `frontend/04-casca-e-personas.md` (a casca e
o `Can`).
**Entrega:** as telas com que uma organização administra a si mesma — quem tem acesso, quem foi
convidado e ainda não entrou, e com quem ela tem convênio.

## Objetivo

Tirar do `psql` a administração do dia a dia de um tenant. Hoje `GET`/`PATCH /membros`,
as três rotas de convite e as três de convênio existem, estão testadas e **nenhuma tem tela** —
convidar alguém é `curl`, e revogar um convite mandado por engano era `UPDATE` no banco até a
`backend/08`, que deu a rota e disse, no próprio índice, que a tela seria spec de frontend
própria. É esta.

## Fora de escopo

- **Criar organização e ligar/desligar módulo.** São atos da **Plataforma** sobre um tenant, não
  do tenant sobre si mesmo — persona diferente, rota diferente (`/plataforma`), e ganham a
  `frontend/09`. Aqui não há nada de `platform_admin`.
- **Testes de componente e CI.** Adiados por decisão do Kauan em 2026-07-20, junto com a
  `frontend/07`. Vale a mesma regra dali: o que é regra pura ganha teste **nesta** entrega.
- **Link pra `/parceiros/cadastro` no login.** A `frontend/06` registrou que a tela existe e
  ninguém aponta pra ela. **Decidido em 2026-07-21 (Kauan): continua sem link** — o Parceiro não
  se acha sozinho, a Widelab manda o link por fora. O motivo está no `Como ficou` da `frontend/06`
  e importa aqui: Parceiro sem convênio é organização órfã, e convênio é ato da Empresa. Não
  adicione o link "por ergonomia" ao mexer nestas telas.
- **Convidar em massa / importar CSV.** O `POST /convites` é um e-mail por vez. Lote traz
  resultado parcial (quais foram, quais falharam), que é contrato de backend novo.
- **Remover membro de verdade.** Não existe `DELETE /membros/{id}`, e é coerente com o resto do
  produto: desativar é `PATCH status`. A tela não oferece lixeira.
- **Reenviar convite.** Não há rota. O caminho existente é revogar e convidar de novo, que gera
  token novo — e é o certo, porque o token é de uso único. Um botão "reenviar" que faz
  `DELETE` + `POST` escondendo isso mentiria sobre o link antigo ter morrido.

## Duas telas, e onde elas entram no menu

```
/organizacoes/[orgId]/pessoas     → Membros | Convites   (abas)
/organizacoes/[orgId]/parceiros   → Convênios
```

**Membros e convites são a mesma pergunta em dois tempos** — "quem tem acesso a esta
organização" e "quem foi chamado e ainda não entrou" —, então são abas de uma tela só e não dois
itens de menu. É também o que o backend já sugere: `GET /convites` **sem `?status=` devolve só os
pendentes**, porque "a pergunta que a tela faz primeiro é o que ainda está de pé pra alguém
aceitar". A aba Convites abre exatamente nessa lista.

### `buildNav` passa a receber `permissions`

Estes itens **não são módulos** — são do kernel, e o `buildNav` hoje monta "Início" mais um item
por módulo contratado. Ele ganha um terceiro grupo, e pra decidi-lo precisa das capabilities:

| Item       | Aparece com                              |
| ---------- | ---------------------------------------- |
| Pessoas    | `members.read`                           |
| Parceiros  | vínculo de organização `company`/`partner` (a rota não exige capability) |

**Capability e não persona**, pela mesma razão da `frontend/07`: `company_admin`, `hr` e
`partner_admin` são três personas diferentes que precisam de Pessoas, e `finance`, `manager` e
`collaborator` são a mesma persona de umas e não precisam. Persona aqui acertaria por acidente.

O ganho colateral é o único teste sério desta entrega: `buildNav` é **função pura e já testada**
(está entre os 61 que rodam hoje), então a regra de visibilidade destas telas nasce com rede,
diferente das telas em si.

## Pessoas → Membros

`GET /organizacoes/{orgId}/membros` (`members.read`), paginado. Colunas: nome, e-mail, papel
(pelo `ROLE_LABEL`, que já existe) e status.

Editar é `PATCH /membros/{id}` com `role` e/ou `status` — e **só** isso: criar membro é convite
(`backend/06`), e a tela diz isso no estado vazio e no lugar do botão "Adicionar" que as pessoas
vão procurar. O botão existe, chama-se **"Convidar"**, e leva pra aba ao lado.

O select de papel oferece só os papéis válidos **para o tipo desta organização**
(`ROLES_BY_ORGANIZATION_TYPE`): cinco numa Empresa (`company_admin`, `hr`, `finance`, `manager`,
`collaborator`), dois num Parceiro (`partner_admin`, `partner_operator`). O mapa é espelhado em
`features/context/lib/roles.ts` — não vem do backend, porque não há rota que o exponha. Mexeu no
mapa do domínio, mexe aqui; é a mesma disciplina que o `MODULE_CATALOG` já carrega, e o custo de
errar é baixo (422 legível, com a lista de papéis válidos na mensagem).

Quem tem `members.read` mas não `members.write` — o caso do `hr` — vê a lista **sem** os controles
de edição. `<Can permission="members.write">` em volta deles.

### O furo que a tela não pode fechar: nada impede se rebaixar

`UpdateMembershipUseCase` **não guarda nada** além de papel×tipo: um `company_admin` pode mudar o
próprio papel pra `collaborator`, ou desativar o próprio vínculo, e a organização fica sem quem a
administre — sem erro, sem aviso, e sem caminho de volta que não seja `platform_admin` ou CLI.
Vale igual pro último `partner_admin`.

**Esta spec não conserta isso, e é decisão consciente.** O `Can` é explícito: esconder o botão é
ergonomia, quem nega é o backend, e "um `<Can>` sem `require_permission` do outro lado é um
cadeado pintado". Um `if (membership.id === meuId) return` na tela seria exatamente isso — parece
proteção, some no primeiro `curl`, e faz todo mundo achar que o caso está tratado. O conserto é
regra de domínio (422 no auto-rebaixamento e no último administrador ativo) e é **spec de
backend**, achada ao escrever esta.

O que a tela **faz** é o que lhe cabe: marca a própria linha ("você") e pede confirmação
nomeando a consequência quando a ação é sobre si mesmo. Confirmação é honestidade sobre um risco
real, não um cadeado fingindo ser guard.

## Pessoas → Convites

`GET /organizacoes/{orgId}/convites` (`invitations.read`), paginado, **abrindo nos pendentes**.
Um filtro de status permite ver o histórico; ele vai pra URL como `?status=`, igual ao backend.

O `status` de cada item é o **efetivo** — um convite vencido chega como `expired` mesmo com a
coluna em `pending`, e a tela só exibe o que recebeu. **Não recalcule vencimento comparando
`expires_at` com o relógio do navegador**: seria a terceira escrita de uma regra que a
`backend/08` já registra como dívida por existir duas vezes (Python e SQL), e a única das três
rodando num relógio que o servidor não controla.

| Status efetivo | Ação na linha            |
| -------------- | ------------------------ |
| `pending`      | **Revogar**              |
| `expired`      | Convidar de novo         |
| `revoked`      | Convidar de novo         |
| `accepted`     | nenhuma (virou membro)   |

Revogar é `DELETE /convites/{id}` e é **terminal** — o diálogo diz isso, porque "um convite
revogado não reativa, reconvidar é criar outro com token novo". O 409 sobre um convite já aceito
não deveria acontecer pela tela (a linha não tem o botão), mas se acontecer — a lista envelheceu
numa aba aberta — a mensagem é a certa: essa pessoa já entrou, e tirar o acesso dela é na aba
Membros. O 204 sobre um já revogado é idempotente e a tela trata como sucesso.

**O token nunca aparece**, porque a resposta nunca o traz: ele é credencial do convidado, não de
quem convidou. Não há "copiar link" nesta tela, e o motivo fica escrito no código pra ninguém
"consertar" isso depois.

Convidar é um formulário de dois campos (e-mail e papel) que responde 201 e a lista recarrega.

## Parceiros → Convênios

`GET /organizacoes/{orgId}/convenios` **não exige capability** — só o vínculo com a organização
do path — e "serve à Empresa e ao Parceiro". É uma tela, dois sentidos de leitura, e o título
muda com o tipo da organização ativa: numa Empresa é "Parceiros", num Parceiro é "Empresas
atendidas". O mesmo dado, a mesma rota; só o rótulo sabe de que lado se está.

Mutar é `agreements.write`, que **só o `company_admin` tem** — nem `platform_admin`, e isso é
decisão da `backend/03` (conveniar é ato da Empresa). Então:

- na Empresa, com `agreements.write`: criar convênio (`POST`, escolhendo o Parceiro) e
  suspender/reativar (`PATCH status`);
- no Parceiro: **leitura pura**, sem exceção. Não há botão pedindo convênio — o Parceiro não tem
  a rota, e um botão que só produz 403 é pior que a ausência dele.

Criar convênio precisa escolher um Parceiro pelo `partner_id`, e aqui há um limite real: **não
existe rota que liste Parceiros disponíveis pra uma Empresa.** `GET /organizacoes` é
`organizations.read`, de `platform_admin`. Então o campo é o `partner_id` colado, com o texto
dizendo de onde ele vem — e fica registrado que a ergonomia certa (buscar Parceiro por nome ou
documento) é **rota nova de backend**, não algo que a tela resolve. É o segundo achado desta spec,
irmão do hodômetro da `frontend/07`.

## Critérios de aceite

1. Um `company_admin` vê "Pessoas" e "Parceiros" no menu; um `collaborator` na mesma Empresa não
   vê nenhum dos dois, e as rotas na mão respondem com o estado de acesso negado da casca.
2. Um `hr` vê "Pessoas", lista os membros e **não** tem controles de edição de papel; a aba
   Convites funciona inteira pra ele (listar, convidar, revogar).
3. Convidar por e-mail e papel cria o convite, ele aparece na aba Convites como `pending`, e o
   link do log do `LoggingEmailSender` leva à tela de aceite da `frontend/06`.
4. Revogar um convite pendente o tira da lista padrão; filtrando por `revoked` ele aparece com o
   status, sem ação disponível.
5. A aba Convites abre **só com os pendentes** sem nenhum filtro aplicado; um convite cujo
   `expires_at` já passou aparece como "Expirado" — e continua assim se o relógio do navegador
   estiver adiantado ou atrasado, porque quem decide é a resposta.
6. Nenhuma tela desta spec exibe o token de um convite (verificável com o inspetor: nem no DOM,
   nem no payload que a tela recebe).
7. Mudar o papel de um membro reflete na lista; escolher um papel que não existe no tipo da
   organização não é oferecido pelo select, e o 422 do backend (caso chegue) mostra a lista de
   papéis válidos.
8. Editar a **própria** linha pede confirmação nomeando a consequência — e, se confirmada, ela
   acontece, porque o backend a permite. O comportamento fica registrado como furo de backend,
   não como bug desta tela.
9. Num Parceiro, `partner_admin` vê "Empresas atendidas" em leitura pura, sem nenhum botão de
   criar ou suspender.
10. Numa Empresa, `company_admin` cria um convênio informando o `partner_id` e o suspende em
    seguida; a lista reflete o status.
11. `buildNav` ganha teste pros itens novos (com e sem `members.read`), somando aos 61 atuais;
    `npm run typecheck` e `npm run lint` limpos.

## Os dois achados que viram spec de backend

Escrever esta spec encontrou duas coisas que **não** são de frontend, e ficam registradas aqui
porque é onde doeram:

1. **`PATCH /membros/{id}` não impede auto-rebaixamento nem a remoção do último administrador
   ativo.** É perda de acesso administrativo sem caminho de volta dentro do produto. Spec de
   backend, e a mais urgente das duas.
2. **Não há rota pra uma Empresa descobrir Parceiros.** `GET /organizacoes` é de `platform_admin`,
   então o convênio nasce com um UUID colado. Spec de backend (busca de Parceiro por nome/documento,
   provavelmente escopada a quem já tem convênio ou pública entre tenants — que é decisão de
   produto).
