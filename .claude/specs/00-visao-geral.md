# Superapp Widelab — Visão geral

> Documento raiz. Registra o que estamos construindo, em que ordem, e quais decisões
> já foram tomadas — inclusive as que decidimos **não** tomar ainda.
> Última revisão: 2026-07-20.

## O que é

Uma plataforma web **multi-tenant** que hospeda vários serviços internos ("apps") sob um
mesmo núcleo de identidade, organizações e permissões. Os dois primeiros serviços serão
**Refeições** (controle dos "tickets" deixados em restaurantes, hoje acertados no papel uma
vez por mês) e **Carro** (registro de uso da frota — condutor, quilometragem e horários,
hoje preenchidos numa folha).

Nasce pra resolver dores internas da Widelab, mas é construída desde o dia zero pra ser
**vendida a outras empresas**. Referência visual: o protótipo em
`planolabbeneficios.lovable.app`.

**Distinção que atravessa todo o projeto:** o **superapp** (o núcleo/plataforma) é uma coisa;
os **apps de negócio** (Refeições, Carro) que plugam nele são outra. **Esta fase entrega só
o núcleo.** Os apps vêm depois e não devem exigir mudança no núcleo pra existir.

## Atores

| Ator            | O que é                                                                                              | Escopo                                                                                |
| --------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| **Plataforma**  | A Widelab como operadora do SaaS.                                                                    | Administra tenants, módulos, faturamento da própria plataforma.                       |
| **Empresa**     | O tenant/cliente que contrata a plataforma. **A Widelab é o tenant nº 1** (dogfood).                 | Habilita módulos, tem Colaboradores, define papéis internos (RH, Financeiro, Gestor). |
| **Parceiro**    | Ex.: o restaurante. Organização de **primeiro nível** — cadastra-se uma vez e atende **N Empresas**. | Portal próprio (ler QR, registrar consumo, acompanhar faturas).                       |
| **Colaborador** | Pessoa vinculada a uma Empresa.                                                                      | App próprio (carteira, saldo, QR de identificação, extrato).                          |

## Decisões tomadas

**Monólito modular, não microserviços.** Um backend, um frontend, um Postgres. A unidade de
deploy é o **processo/container**, não o módulo — atualizar um serviço = rebuild de um
container, rolling, zero downtime, sem tocar frontend nem banco. Isso entrega ~90% do
"mexer no Carro sem mexer no resto" **sem** o custo de sistemas distribuídos (bancos
separados, chamadas de rede entre módulos, contrato versionado, transação distribuída).
Fazer microserviço agora seria pagar o custo antes de ter o problema.

**Seams de extração desenhados, não usados.** O backend segue hexagonal por módulo: um
módulo **nunca importa outro módulo direto**, só o `core` via portas, e **módulo novo não
toca `src/core`**. Essa fronteira é o que torna um módulo _destacável_: no dia que o Carro
precisar escalar/deployar sozinho, ele vira um FastAPI próprio atrás do mesmo nginx em
`/api/carro/*`, com schema próprio, sem reescrever a lógica. Projetamos pra esse dia ser
**barato**, não pra ele ser **hoje**.

**Backend FastAPI hexagonal; frontend Next (só frontend).** A lógica de verdade daqui é
backend pesado (workflow de fatura, cálculo de split, tenancy, papéis) e a casa já é forte
em Python. O Next é **só a camada de frontend** e consome a API FastAPI — não usamos as
route handlers do Next como backend. Preserva a convenção da casa e a história de extração
de módulos.

**Multi-tenant de verdade, com autorização no núcleo.** Aqui é o **oposto** da Central de
Aplicações: lá a decisão foi _"autentica, não autoriza"_, porque os apps já existiam com
regras divergentes que ela não podia unificar. Aqui, o modelo compartilhado de organização,
papéis e tenancy **é o produto** — uma Empresa cadastra suas pessoas, seus parceiros e seus
papéis **uma vez** e isso vale pra todos os serviços. Sem isso, seria N mini-sistemas
isolados com um menu em cima, não um superapp.

**Parceiro é organização de primeiro nível.** Não é filho de uma Empresa. Ele se liga a
cada Empresa por um **convênio** — um vínculo que carrega os termos _por Empresa_ (catálogo,
preços, regras de subsídio). Um mesmo restaurante atende várias Empresas com preços
diferentes, exatamente como o protótipo promete.

**Uma organização tem um tipo só, definido na criação e imutável.** `platform`, `company`
ou `partner` — nunca os três acumulados. Uma pessoa jurídica que precise ser Empresa _e_
Parceiro ao mesmo tempo não é caso do produto agora; se um dia for, o caminho é migrar
`type` para _papéis de organização_ — migração deliberada, não corrupção silenciosa. A
integridade (o tipo certo em cada lado do convênio, e o tipo não mudando sob um convênio
existente) é garantida no banco, não só na aplicação — ver `backend/03-organizacoes-e-tenancy/spec.md`.

**Identidade própria, atrás de uma porta trocável.** O superapp possui login próprio porque
tem usuários que **nunca** estarão na Central (funcionários de outras Empresas clientes e
Parceiros) e porque o SSO da Central é fase futura lá deles. A fonte de identidade fica
atrás de uma porta fina: ligar "entrar com a Widelab" (Central via JWT RS256/JWKS) depois
não deve tocar **uma linha** da autorização.

**Cada Empresa só enxerga os módulos que contratou — entitlement por tenant, com negação por
padrão.** Quando uma Empresa é provisionada, a Plataforma (Widelab) marca quais módulos ela
comprou (Refeições, Carro, …); só esses ficam liberados, e o padrão é _tudo negado_ até ser
explicitamente ligado. A habilitação é um **flag por tenant**, não um runtime de plugins —
módulos são módulos de compilação, nada de carregar plugin dinâmico. O flag é imposto nas
**duas pontas**: o backend **rejeita (403)** qualquer requisição a um módulo que o tenant não
tem ligado — não basta esconder no frontend —, e o frontend só monta a navegação e as
personas dos módulos liberados. Vender um módulo novo pra um cliente é ligar um flag, sem
deploy. Detalhe em `backend/05-modulos-e-entitlements/spec.md` e `frontend/04-casca-e-personas/spec.md`.

**Uma única app Next, com personas por route group.** As três "caras" do produto (Painel
Admin, Portal do Parceiro, App do Colaborador — os três portais do rodapé do protótipo)
vivem no **mesmo** app Next, em route groups (`(admin)`, `(parceiro)`, `(colaborador)`),
compartilhando o design system. A navegação é _consciente de persona_: cada usuário vê só
as superfícies e módulos a que tem direito, derivados dos seus vínculos e entitlements. O
app do Colaborador pode virar PWA instalável dentro do mesmo app quando fizer sentido. O
seam natural do frontend é por **persona**; o do backend é por **módulo** — nenhum dos dois
é partido agora.

**Nomes de tabela normais.** `snake_case` no plural (`users`, `organizations`,
`memberships`, `module_entitlements`, …). **Sem** o prefixo `T0xx` da Central.

**Rotas em português; tenant no path.** Os caminhos da API são em português
(`/api/auth/login`, `/api/organizacoes/{orgId}/convenios`). A organização ativa
viaja no **path** (`/api/organizacoes/{orgId}/...`), nunca em header nem em sessão — a
requisição é autoexplicativa, não há "organização default" implícita, e a URL do frontend é
compartilhável por organização. Só as **rotas** são em português; nomes de tabela, coluna e
valores de enum seguem em inglês `snake_case`.

## Convenções herdadas

Da casa (Central / receipt-reader), não inventadas aqui:

- **Backend:** `src/core` intocável por módulos, `src/modules/<módulo>/` em camadas
  (`domain` → `application` → `adapters`), `application` recebe repositório via `Depends` e
  nunca importa `adapters`. Postgres **async**, schema **só** via Alembic (sem
  `create_all`), `uv` + `ruff format` + `ruff check` + `mypy`. E-mail é `CITEXT`; senha é
  Argon2id, nunca bcrypt. **Ajuste:** nomes de tabela sem `T0xx`.
- **Frontend:** TypeScript strict, Tailwind, shadcn/Radix, **TanStack Query**, **zod** (tipos
  sempre `z.infer`, nunca escritos à mão), estrutura por feature, tema escuro. **Diferença
  da Central:** roteamento é do **Next (App Router)**, não TanStack Router.

## Fases

| Fase                         | Escopo                                                                                                                                                | Estado               |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| **1 — Núcleo da plataforma** | Identidade + sessão, organizações + tenancy, membros + autorização, entitlements de módulo, casca + personas, login. **Nenhum app de negócio ainda.** | Fechada              |
| **2 — App Carro**            | Cadastro de veículos e condutores, registro de uso (retroativo: condutor, km, horários), relatório de quilometragem.                                  | **Em implementação** |
| 3 — App Refeições            | Catálogo/preços por convênio, consumo via QR, cálculo de split, workflow de fatura, acerto com o Parceiro.                                            | Não iniciada         |

**Onde a fase 1 está (2026-07-16):** a **fase 1 está fechada** — backend `01`–`07` e frontend
`01`–`06`. Dá pra **entrar no sistema pela tela** (convite ou auto-cadastro de Parceiro), logar,
cair na cara certa da sua persona — com a navegação saindo dos módulos que o seu tenant
contratou — e **trocar de organização** quando se pertence a mais de uma. O eixo de identidade
fecha de ponta a ponta; o `access` fechou os
eixos de **autorização** e **entitlement**: `backend/03` entregou `organizations`, o convênio
Empresa↔Parceiro e o contexto de tenant; `backend/04` entregou `memberships`, os papéis por
tipo de organização, o `require_permission` e a persona; e `backend/05` entregou o
`ModuleRegistry`, `module_entitlements`, o `require_module` e o contrato de plugagem. Dá pra
subir a stack, logar, provisionar Empresas e Parceiros, conveniá-los, vincular pessoas com
papel, **vender um módulo ligando um flag** — e **o backend nega de verdade**: 403 em tenant
sem vínculo, 403 em permissão faltante e 403 em módulo não contratado.

**Entrar no sistema deixou de ser CLI.** A `backend/06` fechou os dois caminhos de entrada de
gente: o Colaborador/staff é **convidado** pela Empresa (`hr`/`company_admin`), aceita por um
token opaco de uso único e já sai com senha, vínculo e sessão; o Parceiro **se auto-cadastra**
(organização + primeiro `partner_admin` + sessão, numa transação atômica) e é associado a cada
Empresa pelo convênio da `03`. A CLI de `grant` continua existindo pro bootstrap do primeiro
`platform_admin` — que, esse sim, não tem quem o convide.

**O guard de vínculo permissivo da `03` caiu.** Qualquer usuário autenticado alcançava qualquer
organização ativa porque vínculo era `memberships`; agora `current_organization` confere o
vínculo e afrouxa só pra `platform_admin`. O multi-tenant é real.

**Entitlement não afrouxa nem pra Widelab.** `require_permission` afrouxa pra `platform_admin`;
`require_module` não afrouxa pra ninguém — um módulo que a Empresa não comprou não abre pra
ninguém, porque é fato comercial e não privilégio. `GET /api/organizacoes/{orgId}/me` já
devolve `modules`.

**Entrar no sistema deixou de ser `curl`.** A `frontend/06` deu tela aos dois caminhos que a
`backend/06` abriu: `/convites/[token]` (público) mostra Empresa, e-mail e papel, define a senha
e já cai na persona; `/parceiros/cadastro` cria o Parceiro, o primeiro `partner_admin` e a
sessão. Com a `frontend/05`, quem tem mais de um vínculo **troca de organização pelo seletor do
masthead**, e o pós-login volta pra última organização visitada; trocar de organização é navegar
pra outro `orgId`, e o cache do TanStack se separa sozinho porque as chaves o incluem.

**O que falta agora não é fase 1:** é **CI** (a `backend/07` a deixou como spec seguinte) e a
**infra de teste de componente** do frontend (testing-library + jsdom) — a dívida que as `04`,
`05` e `06` registraram, e que a `06` agravou: os dois formulários de onboarding são hoje os
maiores clientes sem teste do projeto.

**As duas foram adiadas de propósito em 2026-07-20, e as telas vêm antes.** A decisão é do Kauan
e o motivo era o desequilíbrio que a `backend/10` deixou visível: o backend estava duas fases à
frente do frontend, que consumia **7 das 37 rotas**. CI e teste de componente protegem código que
existe; o que faltava era código que não existia. As três specs de tela (`frontend/07`–`09`)
vieram primeiro, cada uma carregando a regra de que **o que é função pura ganha teste na própria
entrega**, pra a dívida parar de crescer sem rede enquanto a infra não chega.

**Em 2026-07-21 as `07` e `08` foram implementadas** — em duas worktrees em paralelo, com um único
conflito no merge (`components/ui/table.tsx`, criado pelas duas). A frota e a gestão da organização
têm tela, sobrou a `09`, e a suíte pura foi de **61 para 180 testes**. A regra da função pura
segurou 112 deles, então ela funcionou. Mas a dívida de componente **cresceu como previsto**: seis
telas novas de formulário sem cobertura de DOM, e as duas entregas nem chegaram a subir a stack —
foram escritas contra os contratos lidos no código do backend e checadas por `build`. Quem
escrever a spec de teste de componente começa pelo formulário de viagem da `frontend/07`.

**A fase 3 começou antes da 2, e de propósito.** A `backend/10` entregou a **Frota** — o primeiro
app de negócio do superapp, e a prova de que o desenho das `05`/`09` aguenta: `src/modules/frota/`
tem schema, 14 rotas e sete capabilities, importa **só** `src.core`, e o `src/core` não mudou em
nenhuma linha. Um `manager` — papel que sai de `PERMISSIONS_BY_ROLE` com `frozenset()` vazio —
cadastra veículo e lança viagem porque o `grants` do descritor chega até ele. Falta a `frontend/07`
com as telas. **O que a frota cobrou de dívida foi a fronteira**: `PageResponse`,
`get_page_params` e `_pg_enum` moram no `access`, um app de negócio não pode importá-los e o
critério da spec proibia promovê-los ao `core` — então estão duplicados, e Refeições vai duplicar
de novo. Promovê-los é spec própria. E descobriu-se que o **`alembic check` nunca esteve limpo**:
as FKs que cruzam módulo vivem só na migration desde a `0003`, e ele propõe dropar seis delas —
o que a spec de CI vai ter que tratar com allowlist. **A `backend/11` levou a lista pra sete**, e
a `0007` mostrou que o número não é folclore: a primeira versão dela deixava **oito**, porque uma
FK interna ao `frota` tinha ficado fora do model por engano. Quem mexer nisso rode o comando.

**Em 2026-07-22 a `backend/11` entregou a leitura de hodômetro por foto**, e ela é a primeira spec
do projeto a fechar com um critério de aceite **em aberto e assumido**. Todo o desenho está de pé
e testado — porta de storage no `core`, porta de leitura no módulo, `current_odometer` derivado
sem N+1, a foto como evidência — mas o motor de verdade nunca rodou: as fotos do bake-off que a
spec cita **nunca foram commitadas** (`.claude/spikes/` não existe no repo) e não há chave de
fornecedor. Sem ela o sistema **se abstém**, que é o comportamento honesto e o que faz o formulário
continuar utilizável. Isso deixa duas lições registradas: **anexo de spec tem que ir pro repo na
mesma entrega** (a tabela de medição do Tesseract hoje não é reproduzível a partir deste clone), e
**código atrás de porta ainda é código não exercitado** — o adaptador da OpenAI e o do S3 estão os
dois nessa categoria.

**A `/parceiros/cadastro` não tem link em lugar nenhum, e isso é decisão** (Kauan, 2026-07-21).
A `frontend/06` a entregou funcionando e nenhuma tela aponta pra ela — chega-se por URL direta, e
**fica assim**: quem manda o link é a Widelab, por fora. O Parceiro não se acha sozinho porque um
Parceiro sem convênio é organização órfã — convênio é ato da Empresa (`agreements.write`, que nem
`platform_admin` tem), e um restaurante que se cadastra por conta própria não atende ninguém e
ainda ocupa o próprio e-mail pro cadastro combinado que viria depois. O auto-cadastro é atalho pra
quem já foi chamado, não porta de descoberta. **A ausência do link é a decisão** — não a
reintroduza por ergonomia.

**As telas acharam quatro furos de backend**, todos por olhar um contrato do lado de quem o
consome — que é o que uma tela faz e nenhuma spec de backend tinha feito. Os três primeiros
saíram de **escrever** as specs (`frontend/07`–`09`, 2026-07-20); o quarto saiu de
**implementá-las** (2026-07-21), o que é a diferença entre prever o contrato e usá-lo:

1. ✅ **`PATCH /membros/{id}` não impede auto-rebaixamento nem a perda do último administrador.** Um
   `company_admin` se rebaixa a `collaborator` e a organização fica sem quem a administre, sem
   erro e sem caminho de volta dentro do produto. É o mais urgente. A tela **não** o disfarça: um
   `if` no frontend seria o "cadeado pintado" que o `Can` proíbe.
   **Fechado em 2026-07-23:** ninguém edita o próprio vínculo — papel **e** status, 422. E a
   segunda metade caiu por consequência, sem virar regra: se cada um só edita os outros, sempre
   sobra pelo menos um administrador, então "último administrador ativo" não precisou de consulta
   nenhuma. Só então os controles sumiram da própria linha na tela — antes disso teriam sido o
   cadeado pintado. Ver `backend/04` e `frontend/08`, seções "Depois".
2. **Uma Empresa recém-provisionada não ganha o primeiro membro por tela nenhuma.**
   `platform_admin` não tem `invitations.write` (decisão da `08` — convidar é ato da organização),
   `POST /membros` não existe, e a organização nova não tem ninguém pra convidar o primeiro.
   Corolário: a CLI tem **dois** casos, não um — o `CLAUDE.md` afirmava um. Ver `frontend/09`.
   **Decidido em 2026-07-21 (Kauan): `POST /organizacoes` passa a aceitar o e-mail do primeiro
   administrador e cria o convite na mesma transação** — como o auto-cadastro de Parceiro já faz.
   Assim uma Empresa nunca existe sem caminho de entrada, e a decisão da `08` fica de pé: o convite
   nasce **da organização, no instante em que ela nasce**, não de um `platform_admin` com
   capability emprestada. É **spec de backend ainda não escrita**, e ela **bloqueia a
   `frontend/09`**.
3. **Não há rota pra uma Empresa descobrir Parceiros** — `GET /organizacoes` é de
   `platform_admin`, então criar convênio começa por colar um UUID.
4. ✅ **`MemberResponse` não devolve nome nem e-mail, e nenhuma rota traduz `user_id` em pessoa.**
   Achado ao implementar, em 2026-07-21. A lista de membros mostra UUID e o select de condutor da
   frota mostra `papel · <8 caracteres>`; pior, o e-mail de quem foi convidado **aparece** na aba
   Convites e **some** quando a pessoa aceita — vira membro e perde o nome. Cruzar as duas listas
   no cliente não resolve: o convite não devolve `user_id`, então o join seria palpite. O que
   torna este o mais forte dos quatro é **como** apareceu: as `07` e `08`, implementadas em
   paralelo e sem contato, esbarraram nele pelos dois lados. Ou `MemberResponse` ganha
   `name`/`email`, ou o kernel ganha uma rota de diretório — é decisão de backend.
   **Fechado em 2026-07-23 pela primeira saída, e não pela segunda:** a rota de diretório teria
   aberto superfície nova de leitura de identidade; ficou um verbo a mais na porta que já existe
   (`UserReader.list_profiles_by_ids`, implementada pelo `auth`), com o `ListMembersUseCase`
   cruzando a página. **O `mount_routes` não ganhou linha** — seguem cinco. Os dois consumidores
   foram corrigidos juntos, pelos dois lados por onde o furo apareceu.

**O 3 segue em aberto** — é rota nova (busca de Parceiro), e fica registrado na spec que o achou.

**Os dois buracos que a `backend/06` deixou de propósito foram fechados pela `backend/08`
(2026-07-20).** Não havia rota pra **revogar** nem pra **listar** convites (revogar era `UPDATE`
no `psql`), e um **Parceiro não conseguia crescer** — só Empresa convidava, então o segundo
membro de um Parceiro só nascia pela CLI. Agora `GET`/`DELETE /api/organizacoes/{orgId}/convites`
existem, e o `partner_admin` tem `invitations.read`/`invitations.write` — sem rota nova pro
Parceiro: ele usa as mesmas três, e o `CHECK` do banco já barra papel de Empresa. Nada de
migration. O que a spec cobrou foi a **fronteira do status efetivo**: ele é derivado
(`expired` nunca é gravado), e o filtro `?status=` precisou de um gêmeo em SQL do
`effective_status`, porque filtrar em Python depois de paginar faria o `total` mentir. As duas
escritas da mesma regra são dívida, presa por um teste que as compara item a item. Ver `Como
ficou` da `backend/08`.

**Um furo da casca que a `frontend/04` registrou:** os metadados de navegação de um módulo
(label, path) moram **no frontend**, não no contexto — o `/me` devolve `modules` como lista de
chaves, e o `ModuleNav` do descritor só sai pelo `GET /modulos`, que é de `platform_admin`.
A promessa comercial fica de pé (ligar o flag faz o item aparecer sem deploy), mas a spec supunha
o contrário. Ver `Como ficou` da `frontend/04`.

**A dívida de teste do backend foi paga (`backend/07`, 2026-07-16).** O que era `curl` + `psql`
uma vez agora são **69 testes em ~13s**, contra Postgres de verdade e com o schema saindo de
`alembic upgrade head`: o uso único do token, a resposta uniforme do aceite e a atomicidade do
auto-cadastro — propriedades que somem numa refatoração sem ninguém notar — quebram a suíte se
alguém as desfizer. **Teste deixou de ser opcional no backend**: a regra está no `CLAUDE.md` e no
passo 4 da `implementar-spec`, e o opt-in que causou a dívida (_"specs que citam testes"_) morreu.

**As dívidas que seguem abertas antes da fase 2** (as duas primeiras **adiadas** em 2026-07-20 —
ver acima): **CI** — sem ele, a rede depende de `uv run
pytest` antes do commit; é spec própria, separada porque runner, segredo e Docker-no-CI são
problema de infra. A **dívida de teste do frontend** continua inteira e ganha spec própria: as
regras puras (`nav.ts`, `home-path.ts`) têm teste, mas a casca, os guards, o `Can` e o seletor de
organização da `05` foram verificados só a olho, uma vez, no browser — e o `lib/last-org.ts`, que
engole falha de `localStorage`, não tem rede nenhuma. O furo de **capability de módulo** que a
`05` registrou **foi fechado pela `backend/09`**: o descritor declara `grants` e o
`PermissionReader` os soma, então o primeiro endpoint da frota já tem como ser autorizado. O que
sobrou dele é menor e está no `Como ficou` da `09` — o `/me` e o guard somam a permissão em dois
lugares que nada obriga a concordar.

O faseamento é desenhado pra que os apps (fases 2+) **não toquem no núcleo**: cada um entra
como `modules/<app>` no backend + um route group no frontend, ligado por um entitlement. **A
`backend/10` provou a metade backend disso na prática** — a Frota entrou inteira sem uma linha
de mudança em `src/core` —, com a ressalva de que "uma linha em `mount_routes`" virou três
pontos de contato: a linha do `mount_module`, o import dos models em `migrations/env.py` e a
saída do placeholder de `src/api/modules.py`. Nenhum deles é porta de kernel.

## Índice de specs

Implementáveis nesta ordem; cada uma declara suas dependências e o próprio estado no topo.
Todas no formato da casa: `Depende de` / `Entrega` / `Objetivo` / `Fora de escopo` /
`Critérios de aceite`.

**Cada spec é uma pasta com `spec.md` e `como-ficou.md`** (desde 2026-07-22). **Uma spec
implementada não vira documentação do código** — o `spec.md` continua sendo a decisão
registrada e não é reescrito; quando o código divergir dela, a divergência fica anotada no
`como-ficou.md` irmão, não some. Spec ainda não implementada tem só o `spec.md`.

Backend:

1. ✅ `backend/01-fundacao/spec.md` — scaffold FastAPI hexagonal, Postgres async, Alembic, tooling, docker-compose, convenção de nomes.
2. ✅ `backend/02-identidade-e-sessao/spec.md` — usuário, login e-mail+senha (Argon2id), sessão, `GET /me`; a porta trocável pro SSO da Central.
3. ✅ `backend/03-organizacoes-e-tenancy/spec.md` — `Organization` (plataforma/empresa/parceiro), escopo por tenant, o convênio Empresa↔Parceiro. **Guard de vínculo fechado pela 04.**
4. ✅ `backend/04-membros-e-autorizacao/spec.md` — `Membership` (usuário↔org+papel), papéis/permissões, `require_permission`, resolução de persona. **Em 2026-07-23 recebeu as duas dívidas que a `frontend/08` cobrou:** ninguém edita o próprio vínculo (422, e a regra do último administrador caiu por consequência) e a `MemberResponse` ganhou `name`/`email` — por um verbo a mais no `UserReader`, sem rota de diretório e sem linha nova no `mount_routes`. Ver `Como ficou`, seção "Depois".
5. ✅ `backend/05-modulos-e-entitlements/spec.md` — registro de módulo + entitlement por tenant; o contrato que um app de negócio cumpre pra plugar. **Fase 1 do backend fechada.**
6. ✅ `backend/06-convites-e-onboarding/spec.md` — convite/aceite de Colaborador (convidado pela Empresa) e cadastro de Parceiro (auto-registro + associação por convênio). **Fase 1 do backend fechada.** Sem rota de revogar/listar convite, e Parceiro não convida — ver `Como ficou`.
7. ✅ `backend/07-testes/spec.md` — `pytest` + Postgres efêmero (testcontainers), a suíte que prende as invariantes que as `03`–`06` registraram como dívida, e a regra que faz teste deixar de ser opcional no backend. **Pré-requisito da fase 2, pago:** 69 testes, ~13s. Faltam CI (spec seguinte) e `mount_module`, só testável quando o primeiro app de negócio existir — ver `Como ficou`.
8. ✅ `backend/08-gestao-de-convites/spec.md` — listar e revogar convite, e dar ao `partner_admin` o direito de convidar: os três buracos que a `06` deixou de propósito, fechados. Sem migration (o enum já tinha `revoked`, permissão é código); nova capability `invitations.read`. A listagem devolve o status **efetivo** e, sem `?status=`, só os pendentes; revogar é `DELETE` soft por `UPDATE` condicional (409 no já aceito, 404 no de outra org). 235 testes. Fica de dívida o status efetivo escrito duas vezes (Python e SQL) — ver `Como ficou`. A tela de gestão e o link pra `/parceiros/cadastro` seguem sendo spec de frontend própria.
9. ✅ `backend/09-capabilities-de-modulo/spec.md` — o mecanismo que liga capability declarada por um módulo a papel: o descritor declara `grants` (papel→capabilities) e o `PermissionReader` soma os descritores do registry ao mapa do kernel. Sem migration. **O furo que a `05` registrou, fechado — a `backend/10` está destravada.** Capability de módulo é namespaced pela chave e módulo não concede a `platform_admin`; as duas violações derrubam a subida. 86 testes. Fica de dívida a soma duplicada entre o reader e o `/me` — ver `Como ficou`.
10. ✅ `backend/10-frota/spec.md` — o **primeiro app de negócio**: veículos, condutores, registro de uso (retroativo) e relatório de quilometragem. Migration `0006`, com a constraint de exclusão que impede sobreposição de período no mesmo veículo. **O contrato de plugagem das `05`/`09` provado num módulo de verdade: zero mudança em `src/core`.** 216 testes. Ficam de dívida a duplicação de `PageResponse`/`get_page_params`/`_pg_enum` (a fronteira cobrou) e o `alembic check`, que **já não estava limpo antes** — ver `Como ficou`. As telas são spec de frontend própria.

11. ✅ `backend/11-leitura-de-hodometro/spec.md` — fotografar o painel e receber o número: a porta
    `ObjectStorage` no **`core`** (MinIO em produção, disco local de default — o gêmeo do
    `LoggingEmailSender`), a porta `OdometerReader` no `frota` com adaptador OpenAI, e o
    `current_odometer` derivado que **fecha o item que a `frontend/07` pôs fora de escopo**.
    Migration `0007`, sem capability nova. **Implementada em 2026-07-22**, 317 testes — e com
    **um critério em aberto, o mais importante**: o `11` pede a leitura funcionando sobre fotos
    reais, e nem as fotos (`.claude/spikes/` **nunca foi commitado**) nem a chave de fornecedor
    existem neste repo. O `OpenAIOdometerReader` **nunca falou com a OpenAI**; o desenho inteiro
    está testado contra o stub, e o motor é a peça por provar. Sem chave, a leitura **se abstém**
    e o formulário segue utilizável — o gêmeo do convite que sai no log. A allowlist do
    `alembic check` foi de seis pra **sete**, conferida rodando. Ficam de dívida os dois
    adaptadores nunca exercitados (OpenAI e S3) e uma corrida estreita em "leitura já apontada por
    outra viagem", que é a única invariante desta spec fora do banco — ver `Como ficou`.
    **A `frontend/10` está destravada.**

Frontend:

1. ✅ `frontend/01-fundacao/spec.md` — scaffold Next (App Router), TS strict, Tailwind, shadcn, TanStack Query, zod, estrutura por feature, tooling.
2. ✅ `frontend/02-design-system/spec.md` — tokens/tema derivados do protótipo (escuro, acento azul), tipografia, foco, motion.
3. ✅ `frontend/03-login-e-sessao/spec.md` — tela de login, ciclo de sessão, cliente da API de identidade.
4. ✅ `frontend/04-casca-e-personas/spec.md` — app shell, navegação derivada de vínculos + entitlements, guard de acesso. **Fase 1 do frontend fechada.** Não há route group por persona: persona é runtime, route group é estático — ver `Como ficou`.
5. ✅ `frontend/05-selecao-de-organizacao/spec.md` — troca de contexto quando o usuário pertence a mais de uma organização (ex.: Parceiro que atende N Empresas). O último `orgId` visitado passou a ganhar do atalho da Plataforma no pós-login — muda uma decisão da `04`, ver `Como ficou`.
6. ✅ `frontend/06-onboarding/spec.md` — telas públicas de aceite de convite e de auto-cadastro de Parceiro, com o grupo de senha compartilhado. **Fase 1 fechada.** A "terceira tela" do critério 3 (troca de senha logada) nunca existiu, e o critério 4 cede ao 2 no auto-cadastro — ver `Como ficou`.
7. ✅ `frontend/07-telas-da-frota/spec.md` — as telas do primeiro app de negócio: viagens, veículos, condutores e quilometragem, substituindo a rota-placeholder. Um item de menu, quatro telas em abas — módulo não edita a casca. **Tudo o que difere entre pessoas sai de capability, nunca de persona.** O descritor da frota sai do `MODULE_CATALOG` e vira `features/frota/module.ts`, o espelho do que a `backend/10` fez. Fica fora: pré-preencher o hodômetro (falta `current_odometer` no backend) e exportar relatório. **Implementada em 2026-07-21**; o `Como ficou` registra que a spec errou os valores de `agrupar_por` (o enum é `veiculo`/`condutor`) e que o 409 de sobreposição é discriminado por texto de mensagem, porque o `core` devolve `code: "conflict"` pros cinco conflitos de `vehicle_usages`.
8. ✅ `frontend/08-gestao-da-organizacao/spec.md` — pessoas (membros + convites em abas) e convênios: a tela que a `backend/08` nomeou. `buildNav` passa a receber `permissions` pra decidir os itens de kernel. Convite nunca exibe token, e vencimento nunca é recalculado no navegador. **Dois achados viram spec de backend:** `PATCH /membros/{id}` não impede auto-rebaixamento nem a perda do último administrador, e não há rota pra uma Empresa descobrir Parceiros. **Implementada em 2026-07-21**, e um terceiro achado apareceu na implementação: `MemberResponse` não tem nome nem e-mail, então a lista de membros mostra UUID. **Em 2026-07-23 esses dois foram fechados no backend** (422 na auto-edição de vínculo; `name`/`email` na `MemberResponse`, por um verbo novo na porta `UserReader`), e a tela cobrou o preço: os controles saíram da própria linha, a coluna Pessoa virou nome + e-mail, e o filtro de convites perdeu a opção `Pendente` — que duplicava o default sem parâmetro. Ver as seções "Depois" nos dois `Como ficou`. O `Como ficou` também registra duas leituras que a spec não fechava — "Parceiros" segue persona (não existe capability pra usar, porque a rota exige só o vínculo) e `platform_admin` **vê** Pessoas, porque tem `members.read` de verdade.
9. 📋 `frontend/09-console-da-plataforma/spec.md` — tenants e módulos vendidos, dentro da `/plataforma` e **não** na casca do tenant (é a tela de quem vende). Inspecionar tenant não escreve o `last-org`, senão o pós-login cairia no último cliente inspecionado. **Bloqueada:** uma Empresa recém-provisionada não ganha o primeiro membro por tela nenhuma, e a saída decidida (o e-mail do primeiro admin no `POST /organizacoes`, criando o convite na mesma transação) é **spec de backend ainda não escrita** — implementar a `09` antes dela entregaria o console com o caminho que importa ainda passando por CLI.
10. 📋 `frontend/10-foto-do-hodometro/spec.md` — o botão de câmera nos diálogos de lançar e encerrar
    viagem, o hodômetro pré-preenchido com a última leitura do veículo, e a foto visível na viagem
    depois. **Destravada em 2026-07-22**: a `backend/11` entregou as duas rotas, o
    `current_odometer` e o `plausivel` — e é ela
    que **fecha o "pré-preencher o hodômetro" que a `07` pôs fora de escopo**. O recorte guiado foi
    descartado junto com o caminho sem IA. A leitura é **sugestão, nunca valor**: campo editável nos
    três estados, e `plausivel: false` avisa sem bloquear — um `if` no formulário desfaria pela
    porta dos fundos a decisão da `backend/10` de não travar divergência de hodômetro.

## O que não fazer (fora de escopo desta fase)

- Não implementar Refeições ainda — Carro vem antes (ver a tabela de fases), e é ele quem paga o
  mecanismo de capability de módulo (`backend/09`) que os dois precisam.
- Não partir em microserviços, nem criar segundo banco/segundo deploy por módulo.
- Não construir runtime de plugins dinâmico — entitlement é flag por tenant.
- Não acoplar à Central: identidade fica atrás de porta; SSO da Central é ligação futura, ganha spec própria.
- Não usar route handlers do Next como backend.
- Não reintroduzir o prefixo `T0xx` nos nomes de tabela.
