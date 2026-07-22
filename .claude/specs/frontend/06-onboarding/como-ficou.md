# 06 — Onboarding — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Os cinco critérios batem, **com duas ressalvas que mudam o texto e não o código**: a "terceira
tela" do critério 3 nunca existiu, e o critério 4 contradiz o 2 no auto-cadastro — os dois casos
estão abertos abaixo.

A verificação ficou dividida, como nas `04`/`05` e pelo mesmo motivo (não há testing-library no
projeto, e eu não tinha browser). O que **eu** observei rodando, contra a stack de verdade
(Postgres em container, backend nativo, `next dev` com o rewrite `/api/*`): todo o contrato dos
três endpoints, incluindo os 200, 404, 409, 410 e 422 — e pela **origem do frontend**, não só
pela do backend, que é o caminho que a tela faz; a validação compartilhada e as mensagens de
erro, por `npm run test` (61 testes, 25 novos); e o HTML das duas telas novas, que prova a
montagem (o grupo de senha compartilhado sai com os dois campos, `for`/`id` casados, o hint
`aria-describedby` e o "Pelo menos 8 caracteres" vindo da `PASSWORD_MIN_LENGTH`). O que ficou
pro **Kauan observar no browser**: preencher e submeter os dois formulários, o redirect caindo na
casca da persona (**1**, **2**) e o recarregar mantendo sessão e persona (**5**).

O caso de teste, pra repetir: `rh@acme.com.br` (papel `hr` na Acme) convida; o convite sai no log
do `LoggingEmailSender` já apontando pra `http://localhost:3000/convites/{token}` — a
`APP_BASE_URL` da `backend/06` e a rota desta spec se encontraram sem ajuste, o que é a prova
barata de que as duas specs falam do mesmo link.

O que a implementação decidiu, e a spec não previa:

- **A terceira tela do critério 3 não existe, e não foi criada.** O `Reuso` e o critério 3 falam
  em "as três telas com campo de senha", contando "a troca de senha logada (spec 03)". Mas a
  `frontend/03` **não entregou** essa tela: o backend tem `PUT /api/me/password` desde a `02`, e
  o frontend nunca lhe deu UI — `grep password` no `src` antes desta spec achava só o login e o
  design system. Então o `PasswordFields` nasce com **dois** clientes, não três, e o critério 3
  vale pelas duas telas que existem (provado por teste, nos dois schemas). Criar a terceira seria
  escopo que esta mesma spec põe fora ("Aqui só as telas públicas de *entrada*"), e a spec do
  `auth` que a fizer herda o componente pronto: o `label` ("Nova senha") e o `idPrefix` já estão
  lá justamente porque a troca de senha tem **dois** grupos na mesma página (a atual e a nova), e
  dois `id="password"` quebrariam o `<Label htmlFor>`.
- **O critério 4 contradiz o critério 2, e o 2 vence — no auto-cadastro, e só nele.** O 4 pede que
  "nenhuma tela de onboarding" revele conta prévia; o 2 exige que e-mail repetido "mostre conflito
  e leve ao login". Não dá pra ter os dois: o 409 é o contrato que a `backend/06` fixou, e a tela
  não vai mentir sobre o que ouviu. A resolução é a que o domínio já sugere — quem se auto-cadastra
  está reivindicando o **próprio** e-mail, e dizer-lhe "esta conta já existe, entre" é serviço, não
  vazamento; quem abre um convite recebeu um link que **outra pessoa** endereçou, e ali o oráculo
  seria de graça. Então o 4 vale inteiro onde importa: **no convite**. Verificado de propósito, e
  é o achado que fecha o critério — as duas respostas do aceite (conta nova × conta que já
  existia) são **idênticas byte a byte**: mesmo 200, mesmo `content-length: 4`, mesmo corpo
  (`null`). A tela não tem sinal pra vazar, nem se quisesse. E confirmado o outro lado: depois do
  aceite, o `rh@acme` continua entrando com a senha antiga, e a senha mandada no aceite dá **401** —
  convidar um e-mail já cadastrado não é um caminho de redefinir senha alheia.
- **O destino pós-onboarding é a `/`, e não a home do papel aceito montada aqui.** A spec pede
  "redireciona pra home da persona do papel aceito", e a tela **não tem como montá-la**: o
  `GET /api/convites/{token}` devolve o *nome* da organização e nunca o id — "nada de ids internos,
  quem ainda não aceitou não é membro de nada" (`backend/06`). Quem sabe responder isso é a `/`,
  que já é o roteador da `04`: ela lê o `/me/contexto` **já com o vínculo novo dentro** e chama o
  `homePathFor`. Para o convidado sem conta e para o Parceiro recém-criado — o caso comum dos dois
  fluxos — há **um vínculo só**, então o destino é necessariamente o do papel aceito; verificado
  nos dois (`memberships` de tamanho 1, `persona: "collaborator"` num, `persona: "partner"` no
  outro). **A exceção é quem já tinha conta e outros vínculos:** aí vale a ordem da `05` (último
  `orgId` > plataforma > primeiro), que pode não ser a organização do convite. Expor o `orgId` no
  convite público resolveria, mas é decisão da `backend/06` e vira spec nova — não mudei o
  contrato dela por conta própria.
- **O aceite invalida tudo no cache *menos* o convite, e isso é um bug evitado, não uma economia.**
  O login faz `invalidateQueries()` sem filtro porque o cookie mudou, e aqui mudou também. Mas o
  convite acabou de virar `accepted`: buscá-lo de novo responde **410**, e a tela piscaria "convite
  indisponível" no exato instante em que ele funcionou — com a pessoa já logada, olhando um erro.
  O `predicate` exclui a chave do convite, que já não interessa a ninguém.
- **A tela de convite separa 404 de 410 pela saída, não pela causa.** Link torto se copia de novo;
  convite gasto se pede de novo — são ações diferentes, e uma tela só de "convite inválido" mandaria
  metade das pessoas pro caminho errado. Nenhuma das duas mensagens fala de conta (tem teste que
  varre as duas, e as de erro do aceite, procurando `conta|cadastrad|existe`).
- **Nasceu uma feature `onboarding`, e o componente de senha ficou no `auth`.** A spec fixa o
  componente em `features/auth/components` (é dele que a troca de senha vai precisar), mas convite e
  auto-cadastro são domínio próprio — público, sem sessão, e a única parte do app que **cria**
  organização e identidade. O `onboarding` importa `auth` (senha) e `context` (papéis); cross-import
  entre features já era o normal aqui (`context` importa `auth` desde a `04`).
- **`ROLE_LABEL` e `ORGANIZATION_TYPE_LABEL` saíram do `organization-switcher` pra
  `features/context/lib/labels.ts`.** A tela de aceite escreve o mesmo papel que o seletor escreve, e
  duas tabelas divergiriam no primeiro papel novo — a mesma pessoa lendo "RH" numa tela e "hr" na
  outra. Segue valendo que **não** é papel→persona: essa vem pronta do `/me` e o frontend não a
  recalcula.
- **`company_name` vira `companyName` só do lado de cá.** A `backend/06` registrou que o nome do
  campo é confuso (`company` é um tipo de organização *diferente* de `partner`) e apontou o
  rename pra esta spec, "onde o custo é um campo". Mas o payload é contrato do texto desta spec
  também, então o **fio não mudou**: quem renomeia é a `api.ts`, no mesmo lugar onde o formulário
  plano já vira o payload aninhado (`admin: {...}`) — isto é, de graça. A tela diz "Nome do
  parceiro".
- **`expires_at` entra no schema e não é pintado.** É contrato e fica documentado, mas quem diz que
  o convite venceu é o **410 do servidor**, no aceite. Uma data na tela seria uma segunda verdade,
  que envelhece sozinha com a aba aberta. E é `z.string()`, não `.datetime()`: o formato é escolha
  do Pydantic, e um convite bom não pode falhar o parse por causa de como o fuso foi escrito.
- **Sem medidor de força de senha** — a spec o marca "opcional", e ele mediria o que a política não
  cobra: o backend exige **comprimento** e nada mais, então uma barra dizendo "fraca" numa senha que
  ele aceita ensinaria uma regra que não existe. O que a tela mostra é a política real
  (`PASSWORD_MIN_LENGTH`, um número só, que a mensagem do zod e o hint da tela dividem).
- **O e-mail do aceite é `readOnly`, não `disabled`.** Os dois impedem a edição, mas `disabled` tira
  do fluxo de foco e de leitor de tela — e este campo é a informação mais importante da tela (é
  *para quem* o convite é). Com `autoComplete="username"` ele ainda faz o gerenciador de senhas
  guardar a senha nova sob a conta certa.
- **A tela de aceite não barra quem já tem sessão**, diferente do `/entrar` (que tem
  `RedirectIfAuthenticated`). O token é de um **e-mail**, não de uma sessão, e quem decide o que
  fazer com ele é o backend. Barrar aqui trancaria fora justamente quem abriu o link no navegador
  onde já estava logado — o caso mais comum de todos.
- **`/parceiros/cadastro` não tem porta de entrada na UI, e isso virou decisão — não é buraco.**
  Nenhuma tela linka pra ela: o `/entrar` é da `03` e não foi tocado, e esta spec não pede link
  nenhum. Hoje se chega lá **só por URL direta** (o convite, esse, chega por e-mail e o link já
  funciona). Um "É um parceiro? Cadastre-se" no login seria uma linha — não foi feito porque muda
  uma tela entregue e a spec não pediu.
  **Resolvido em 2026-07-21 (Kauan): fica sem link, e o link é a Widelab que manda por fora.**
  O Parceiro **não** deve se achar sozinho. O raciocínio é o do domínio: um Parceiro só serve pra
  alguma coisa depois de ter convênio com uma Empresa, e convênio é ato da Empresa
  (`agreements.write`, que nem `platform_admin` tem). Um restaurante que se cadastra por conta
  própria, sem ninguém esperando por ele, cria uma organização órfã que não atende ninguém — e
  ainda ocupa o e-mail dele, que é o que o 409 vai devolver quando o cadastro *combinado*
  finalmente acontecer. O auto-cadastro existe pra ser **rápido quando alguém já o convidou por
  fora**, não pra ser descoberto.
  **Consequência a respeitar:** não adicione esse link "por ergonomia" numa entrega futura. A
  ausência é a decisão. Se um dia houver aquisição aberta de Parceiro, o que muda não é o link —
  é o domínio (um Parceiro sem convênio precisaria de estado próprio, e não tem).
- **Sem teste de componente, e agora a dívida tem os dois maiores clientes do projeto.** O que tem
  teste é o que dá pra provar sem DOM: a política de senha compartilhada nos **dois** schemas
  (critério 3, pelo comportamento — não pela identidade do objeto) e as mensagens de erro (critério
  4, inclusive varrendo por vazamento). O que não tem é o que mais importa: dois formulários com
  estado, submit, e um redirect. É a mesma dívida que a `04` e a `05` registraram — testing-library
  + jsdom —, e ela já era a candidata óbvia antes desta spec.
- **Achado fora do escopo, e que travava tudo: o `npm install` da `05` nunca rodou.** O
  `@radix-ui/react-dropdown-menu` estava no `package.json` e não no `node_modules`, então o
  `npm run typecheck` falhava e o `next dev` respondia **500 em toda rota** — inclusive nas telas já
  entregues. Não é dívida desta spec nem do código; é a máquina. Rodar `npm install` resolveu, e
  fica o registro de que a `05` fechou sem que o typecheck tivesse rodado depois dela.
- **O `prettier --check` já falhava em 12 arquivos antes desta spec, por fim de linha.** Os arquivos
  estão em CRLF no disco e o Prettier quer LF, então `npm run check` acusa o repositório inteiro.
  Formatei **só** os arquivos desta entrega, com `--end-of-line auto`, pra não afogar o diff numa
  troca de fim de linha do projeto todo. O `.gitattributes` que resolveria isso de vez não existe —
  é dívida de infra, não desta spec.
