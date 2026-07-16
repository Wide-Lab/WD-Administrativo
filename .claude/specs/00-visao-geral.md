# Superapp Widelab — Visão geral

> Documento raiz. Registra o que estamos construindo, em que ordem, e quais decisões
> já foram tomadas — inclusive as que decidimos **não** tomar ainda.
> Última revisão: 2026-07-16.

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
existente) é garantida no banco, não só na aplicação — ver `backend/03-organizacoes-e-tenancy.md`.

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
deploy. Detalhe em `backend/05-modulos-e-entitlements.md` e `frontend/04-casca-e-personas.md`.

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

| Fase                         | Escopo                                                                                                                                                | Estado                |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **1 — Núcleo da plataforma** | Identidade + sessão, organizações + tenancy, membros + autorização, entitlements de módulo, casca + personas, login. **Nenhum app de negócio ainda.** | **Em implementação**  |
| 2 — App Refeições            | Catálogo/preços por convênio, consumo via QR, cálculo de split, workflow de fatura, acerto com o Parceiro.                                            | Não iniciada          |
| 3 — App Carro                | Cadastro de veículos, registro de uso (condutor, km, horários), relatórios.                                                                           | Não iniciada          |

**Onde a fase 1 está (2026-07-16):** o **backend da fase 1 está fechado de verdade** (`01`–`06`)
e o **frontend chegou na casca** (`01`–`04`): dá pra logar e cair na cara certa da sua persona,
com a navegação saindo dos módulos que o seu tenant contratou. O eixo de identidade fecha de
ponta a ponta; o `access` fechou os
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
ninguém, porque é fato comercial e não privilégio. `GET /api/organizacoes/{orgId}/eu` já
devolve `modules`.

**O que ainda falta pra fase 1:** só frontend — a `05` (seletor de organização) e a `06`
(onboarding). Com a `frontend/04` entregue, quem tem mais de um vínculo cai no primeiro: é a
`05` que resolve. A `frontend/06` agora tem backend pronto pra consumir: as telas de aceite
(`GET /api/convites/{token}` é público) e de auto-cadastro de Parceiro.

**Dois buracos que a `backend/06` deixou de propósito, e que o texto dela não previa:** não há
rota pra **revogar** nem pra **listar** convites (revogar é `UPDATE` no `psql` hoje), e um
**Parceiro não consegue crescer** — só Empresa convida, então o segundo membro de um Parceiro
só nasce pela CLI. Nenhum dos dois estava nos critérios; os dois são spec nova. Ver
`Como ficou` da `backend/06`.

**Um furo da casca que a `frontend/04` registrou:** os metadados de navegação de um módulo
(label, path) moram **no frontend**, não no contexto — o `/eu` devolve `modules` como lista de
chaves, e o `ModuleNav` do descritor só sai pelo `GET /modulos`, que é de `platform_admin`.
A promessa comercial fica de pé (ligar o flag faz o item aparecer sem deploy), mas a spec supunha
o contrário. Ver `Como ficou` da `frontend/04`.

**Duas dívidas atravessam a fase 1 e vale decidir antes da fase 2:** não existe **teste
automatizado** de integração nenhum (specs 03/04/05/06 registram; a verificação é `curl` + `psql`) —
e agora o frontend tem a sua versão: as regras puras (`nav.ts`, `home-path.ts`) têm teste, mas a
casca, os guards e o `Can` foram verificados só a olho, uma vez, no browser. E
`ModuleDescriptor.permissions` **não tem mecanismo que ligue capability de módulo a papel** — o
primeiro app de negócio esbarra nisso no primeiro endpoint. Ver `Como ficou` da `backend/05`.

**A dívida de teste ficou mais cara com a `06`, e virou pré-requisito honesto da fase 2.** O uso
único do token, a resposta uniforme do aceite e a atomicidade do auto-cadastro são propriedades
que somem numa refatoração sem ninguém notar — e a verificação delas hoje é manual e não se
repete. Uma spec de infra de teste (`pytest` + Postgres efêmero) deixou de ser "o próximo
candidato óbvio" e passou a ser o que separa a fase 1 de uma fase 2 segura.

O faseamento é desenhado pra que os apps (fases 2+) **não toquem no núcleo**: cada um entra
como `modules/<app>` no backend + um route group no frontend, ligado por um entitlement.

## Índice de specs

Implementáveis nesta ordem; cada uma declara suas dependências e o próprio estado no topo.
Todas no formato da casa: `Depende de` / `Entrega` / `Objetivo` / `Fora de escopo` /
`Critérios de aceite`. **Uma spec implementada não vira documentação do código** — ela
continua sendo a decisão registrada; quando o código divergir dela, a divergência fica
anotada na própria spec (seção `Como ficou`), não some.

Backend:

1. ✅ `backend/01-fundacao.md` — scaffold FastAPI hexagonal, Postgres async, Alembic, tooling, docker-compose, convenção de nomes.
2. ✅ `backend/02-identidade-e-sessao.md` — usuário, login e-mail+senha (Argon2id), sessão, `GET /me`; a porta trocável pro SSO da Central.
3. ✅ `backend/03-organizacoes-e-tenancy.md` — `Organization` (plataforma/empresa/parceiro), escopo por tenant, o convênio Empresa↔Parceiro. **Guard de vínculo fechado pela 04.**
4. ✅ `backend/04-membros-e-autorizacao.md` — `Membership` (usuário↔org+papel), papéis/permissões, `require_permission`, resolução de persona.
5. ✅ `backend/05-modulos-e-entitlements.md` — registro de módulo + entitlement por tenant; o contrato que um app de negócio cumpre pra plugar. **Fase 1 do backend fechada.**
6. ✅ `backend/06-convites-e-onboarding.md` — convite/aceite de Colaborador (convidado pela Empresa) e cadastro de Parceiro (auto-registro + associação por convênio). **Fase 1 do backend fechada.** Sem rota de revogar/listar convite, e Parceiro não convida — ver `Como ficou`.

Frontend:

1. ✅ `frontend/01-fundacao.md` — scaffold Next (App Router), TS strict, Tailwind, shadcn, TanStack Query, zod, estrutura por feature, tooling.
2. ✅ `frontend/02-design-system.md` — tokens/tema derivados do protótipo (escuro, acento azul), tipografia, foco, motion.
3. ✅ `frontend/03-login-e-sessao.md` — tela de login, ciclo de sessão, cliente da API de identidade.
4. ✅ `frontend/04-casca-e-personas.md` — app shell, navegação derivada de vínculos + entitlements, guard de acesso. **Fase 1 do frontend fechada.** Não há route group por persona: persona é runtime, route group é estático — ver `Como ficou`.
5. ⬜ `frontend/05-selecao-de-organizacao.md` — troca de contexto quando o usuário pertence a mais de uma organização (ex.: Parceiro que atende N Empresas). **← próxima do frontend**
6. ⬜ `frontend/06-onboarding.md` — telas de aceite de convite, definição de senha e primeiro acesso por persona.

## O que não fazer (fora de escopo desta fase)

- Não implementar Refeições nem Carro ainda — o núcleo tem que existir e ser plugável primeiro.
- Não partir em microserviços, nem criar segundo banco/segundo deploy por módulo.
- Não construir runtime de plugins dinâmico — entitlement é flag por tenant.
- Não acoplar à Central: identidade fica atrás de porta; SSO da Central é ligação futura, ganha spec própria.
- Não usar route handlers do Next como backend.
- Não reintroduzir o prefixo `T0xx` nos nomes de tabela.
