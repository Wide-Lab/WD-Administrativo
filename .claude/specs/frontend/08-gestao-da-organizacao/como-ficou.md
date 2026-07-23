# 08 — Gestão da organização (pessoas, convites e convênios) — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

As duas telas existem, o menu as mostra pela regra certa e a suíte foi de **61 para 96 testes**
(`npm run test`), com `typecheck`, `lint` e `build` limpos. O que a implementação decidiu, e o que
ela descobriu que a spec não previa:

### O terceiro achado de backend, e é o que mais dói: **membro não tem nome nem e-mail**

A spec manda a lista de membros ter "colunas: nome, e-mail, papel e status". **As duas primeiras
não são implementáveis hoje.** A `MemberResponse` (`access/adapters/http/schemas.py`) devolve
`id`, `user_id`, `organization_id`, `role`, `status`, `created_at` — nada de identidade —, e não
existe rota que traduza um `user_id` em pessoa: `GET /api/me` responde sobre quem pergunta e
`GET /api/me/contexto` também. Varri as 37 rotas; não há um `GET /usuarios/{id}` nem um
`?expand=user`.

Então a coluna "Pessoa" mostra o `user_id` em mono, com um badge **"Você"** na própria linha (que
é possível: `useSession()` dá o meu id). É ruim de usar e está escrito no código que é lacuna do
backend, não escolha da tela — inventar o nome no cliente seria inventar dado.

**O efeito colateral é o que torna isto um achado e não um detalhe:** o e-mail de quem foi
convidado **aparece** na aba Convites e **some** quando a pessoa aceita. Vira membro e perde o
nome. Cruzar as duas listas no cliente não resolve — o convite não devolve `user_id`, então o
join seria um palpite. Isto é irmão dos outros dois achados e merece a mesma spec de backend:
`MemberResponse` precisa de `name`/`email`, ou o kernel precisa de uma rota de diretório.

### A tabela de visibilidade da spec contradiz o critério 1, e o critério venceu

A spec diz que "Parceiros" aparece com "vínculo de organização `company`/`partner`". Tomado ao pé
da letra, isso **inclui o `collaborator`** — ele tem vínculo numa `company`. Mas o critério 1 diz
que "um `collaborator` na mesma Empresa não vê nenhum dos dois". As duas coisas não podem valer.

Ficou pelo critério: **Parceiros aparece pra persona `company_admin` ou `partner`**. Não dava pra
usar capability como em Pessoas porque **não existe uma** — `GET .../convenios` exige só o
vínculo, de propósito, pra servir aos dois lados. O filtro é, portanto, mais estreito que a rota,
e isso está comentado no `KERNEL_NAV`: quem digitar a URL alcança o dado, e o `AccessDenied` que
a tela mostra pro `collaborator` é **ergonomia declarada, não guard**. É a diferença honesta entre
as duas telas — em Pessoas o `AccessDenied` é eco de um 403 real; em Parceiros não é.

### `platform_admin` **vê** "Pessoas", e isso é a regra funcionando

Escrevi o teste esperando que a Plataforma não visse nenhum dos dois ("aqui não há nada de
`platform_admin`") e ele **falhou** — porque `platform_admin` tem `members.read` e `members.write`
de verdade em `PERMISSIONS_BY_ROLE`, para a Widelab consertar o vínculo de um cliente, e o
`require_permission` afrouxa pra ele em qualquer `orgId`. A tela funciona pra ele.

O teste é que estava errado, não o código: esconder Pessoas da Plataforma exigiria um filtro por
persona, que é exatamente o "acertar por acidente" que esta spec manda evitar. Corrigi o teste e
deixei o porquê escrito nele. "Aqui não há nada de `platform_admin`" continua verdade no sentido
em que foi escrito — nenhuma tela **desta** spec é da Plataforma —, mas não implica esconder dela
uma tela do tenant que ela pode operar. Parceiros, esse sim, não aparece: ela não tem
`agreements.write` e não é lado de convênio nenhum.

### Abas e filtro moram na URL

`?aba=membros|convites` e `?status=`. A spec só exigia o `?status=` na URL; pôr a aba junto saiu
de graça e paga: o botão "Convidar" da lista de membros vira navegação de verdade, o voltar do
navegador funciona e a tela é compartilhável — a mesma lógica que põe o `orgId` no path.

**"Pendentes" é a ausência do parâmetro, não `?status=pending`.** `parseStatusFilter` devolve
`null` pra ausência **e** pra valor inválido, e a `api.ts` simplesmente não manda a query. Assim o
default continua sendo do servidor; traduzi-lo aqui criaria uma segunda verdade sobre a mesma
regra. Tem teste de ida e volta (o href que a tela escreve é o que ela sabe ler).

### Sem `@radix-ui/react-dialog` e sem `Select` do shadcn

Nenhum dos dois está instalado, e um segundo agente mexia na mesma árvore em paralelo — instalar
dependência significaria conflito de `package-lock.json`. Então:

- **confirmação** é `<dialog>` nativo com `showModal()`, que entrega prender o foco, Esc e
  backdrop do navegador, sem dependência. Trocar por `<Dialog>` do shadcn depois é substituir
  `confirm-dialog.tsx`, não mexer em quem o chama;
- **select de papel** é `<select>` nativo com as classes do `Input`. Pra 2–5 opções um listbox
  custom perde teclado e o campo nativo do mobile sem ganhar nada.

O único primitivo novo em `src/components/ui/` é `table.tsx`. Ele **desvia** do output padrão do
shadcn num ponto: os tokens de cor. O padrão referencia `text-foreground`,
`text-muted-foreground` e `bg-muted`, que são o tema default do shadcn e **não existem** neste
projeto — e utilidade inexistente não é "cor neutra", é ausência de estilo. Ficaram `text-text`,
`text-muted` e `bg-surface-2`, da paleta de `styles.css`.

### `buildNav` devolvendo itens de kernel quebrou a home, em silêncio

`organization-home.tsx` chamava `buildNav(...).filter(item => item.key !== 'inicio')` pra montar
os cards de "serviços contratados". Com o grupo novo, Pessoas e Parceiros entrariam ali como se
fossem módulos vendidos. Passou a filtrar **pelo catálogo** (`MODULE_CATALOG`), e não por lista de
exclusão, que é o que mantém isso certo quando um módulo novo entrar. Nenhum teste pegaria isso —
achei lendo os chamadores, e é o tipo de coisa que a dívida de teste de componente cobre.

### O que tem teste, e o que não tem

**35 testes novos**, e o critério 11 pedia só os de `buildNav`:

- `nav.test.ts` — o grupo do kernel: com e sem `members.read`, capability atravessando personas
  (`hr` × `finance`, `partner_admin`), o `collaborator` sem nenhum dos dois, a ordem dos grupos,
  os hrefs com `orgId`, e um caso que prende o `includes` de ser frouxo (`frota.vehicles.read`
  não pode destravar Pessoas);
- `roles.test.ts` — o espelho de `ROLES_BY_ORGANIZATION_TYPE`: os cinco e os dois, nenhum papel
  repetido entre tipos, e **cobertura exata do enum** contra o `roleSchema` (um papel sem tipo
  seria um papel que nenhuma tela consegue atribuir);
- `invitation-status.test.ts` — a leitura do `?status=`, a ausência que **não** vira `pending`, o
  valor inválido que cai no default, a tabela de ação por status (cobrindo o enum inteiro) e a
  ida-e-volta do href;
- `organization-error.test.ts` — as traduções, com destaque pro 409 do convite já aceito, que tem
  de mandar pra aba Membros e **não** pode dizer "tente de novo".

**O que não tem teste, e não foi observado:** tudo que é fluxo de tela. Não subi a stack; os
critérios 1–10 descrevem interação (convidar, revogar, editar papel, confirmar, suspender
convênio) e estão implementados contra os contratos lidos no código do backend, **não**
verificados rodando. É a dívida de teste de componente que as `04`–`06` registraram (ver `Fases`
na `00-visao-geral.md`) mais a ausência
de browser nesta sessão — e é exatamente por isso que o critério 11 existe: a regra de
visibilidade é a parte que nasceu com rede.

### Ponta solta consciente

`CAPABILITY_LABEL`, em `organization-home.tsx`, lista as capabilities de kernel em português e
**não** tem `invitations.read`/`invitations.write`, que existem desde a `backend/06`/`08` e têm
guard de verdade. Cabia uma linha cada, mas é escopo que esta spec não pediu — fica anotado em
vez de emendado.

## Depois — 2026-07-23: as duas dívidas cobradas, e um bug que a tela criou sozinha

Três correções na tela de Pessoas. Duas fecham dívidas registradas acima; a terceira é um erro
desta implementação, achado usando a tela.

### A coluna "Pessoa" mostra nome e e-mail

O "terceiro achado" foi consertado onde ele estava: no backend. A `MemberResponse` passou a trazer
`name` e `email`, cruzados por uma porta do `core` (ver o `Como ficou` da `backend/04`), e a tela
só passou a exibir o que recebe — nome em cima, e-mail embaixo, badge "Você" na própria linha.
Nenhuma regra nova aqui, e é assim que devia ser: **a lacuna nunca foi de tela**. O efeito
colateral que estava documentado — o e-mail aparecer na aba Convites e sumir quando a pessoa
aceita — morreu junto.

### Os controles somem da própria linha, e agora isso **não** é cadeado pintado

O comentário em `member-row-form.tsx` mandava não fechar o buraco na tela, e estava certo enquanto
o backend permitia a auto-edição: esconder o controle teria sumido no primeiro `curl` e feito todo
mundo achar que o caso estava tratado. O backend passou a recusar com 422 — papel **e** status —,
e só por causa disso os controles saíram: esconder o que o servidor nega é informar; esconder o
que ele permite é mentir.

No lugar deles, uma frase que diz para onde ir ("só outro administrador edita o seu vínculo"), que
é o que falta quando um "não pode" não tem saída. O `ConfirmDialog` da auto-edição foi junto — ele
pesava um risco que já não é possível correr — e o componente segue vivo, usado pela revogação de
convite.

Um efeito de segunda ordem: o `useUpdateMember` invalidava também o `/me` da organização, e a razão
era exatamente o auto-rebaixamento (quem se editava mudava as próprias permissões, e a casca sai
dali). Sem o caso, aquilo virou uma requisição por edição buscando um contexto que não pode ter
mudado — editar outra pessoa não mexe no meu papel, na minha persona nem nos meus módulos. Saiu, e
o porquê ficou escrito no arquivo, pra voltar junto se a regra um dia mudar.

### O filtro de convites tinha uma opção a mais, e as duas primeiras faziam a mesma coisa

A barra mostrava `Pendentes · Pendente · Aceito · Revogado · Expirado`. O primeiro é o default —
a **ausência** de `?status=`, que a `backend/08` fez devolver só os pendentes — e o segundo é
`?status=pending`, que dá exatamente a mesma lista. Quem clicasse nos dois veria o mesmo resultado
e ficaria sem saber o que tinha entendido errado.

Veio de como as opções eram montadas: `{ value: null } + invitationStatusSchema.options`, ou seja,
o default **mais o enum inteiro**. A decisão de "ausência ≠ `pending`", que está registrada mais
acima e é certa, foi aplicada no parser e no href e esquecida na lista de opções.

Ficaram quatro: `Pendentes` (sem parâmetro) · `Aceitos` · `Revogados` · `Expirados`. **Não há
"Todos"**, e não é esquecimento — a rota não sabe dizer "sem filtro nenhum", e inventar aqui um
valor que ela não aceita daria 422 num clique. Os rótulos estão no plural e por isso **não** saem
do `INVITATION_STATUS_LABEL`: lá eles descrevem um convite numa linha ("Aceito"), aqui nomeiam um
recorte da lista ("Aceitos").

As opções saíram do componente e foram pra `lib/invitation-status.ts`, onde um teste as alcança —
que é o que faltava pro bug ter sido pego. Cinco casos novos, e o que importa não é o que testa o
rótulo: é o que gera o href de cada opção e exige que **nenhum se repita**. Esse pega a classe
inteira do erro, e não o caso de hoje. `npm run test` foi de 180 a 185.
