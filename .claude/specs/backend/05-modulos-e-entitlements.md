# 05 — Módulos e entitlements

**Estado:** ✅ implementada (2026-07-16). Fecha o eixo de entitlement e destrava `frontend/04`
por inteiro. Ver `Como ficou` no fim — em especial o furo do `permissions` do descritor.
**Depende de:** `backend/03-organizacoes-e-tenancy.md`, `backend/04-membros-e-autorizacao.md`.
**Entrega:** o registro de módulos, a tabela de entitlement por Empresa, o guard
`require_module`, e o **contrato que um app de negócio cumpre pra plugar** no superapp.

## Objetivo

Fazer valer a decisão comercial da `00-visao-geral.md`: **cada Empresa só enxerga os módulos
que contratou, negação por padrão, imposto no backend (403) e não só escondido no frontend.**
Vender um módulo novo pra um cliente é ligar um flag, sem deploy.

## Fora de escopo

- Os módulos de negócio em si (Refeições é fase 2, Carro é fase 3). Esta spec entrega o
  mecanismo, com `refeicoes` e `frota` existindo apenas como chaves registradas.
- Cobrança/billing da plataforma (quanto a Widelab cobra por módulo) — spec própria futura.

## Registro de módulos

Em `core`, um `ModuleRegistry`. Cada módulo de negócio declara um descritor e se registra na
subida — **uma linha em `mount_routes`**, coerente com a regra da `backend/01-fundacao.md`:

```python
ModuleDescriptor(
    key="refeicoes",                # estável, snake_case, é PK de várias coisas e vira segmento de rota
    name="Refeições",
    personas=["company_admin", "collaborator", "partner"],
    permissions=["catalog.write", "invoices.approve_hr", ...],
    nav={...},                       # metadados de navegação p/ o frontend
)
```

O registry é a fonte da lista de módulos que a plataforma sabe oferecer. Registrar um módulo
**não toca `core`** além do descritor; um módulo nunca aparece pra um tenant sem entitlement.

## Modelo

`module_entitlements`

| coluna            | tipo                                  | nota                             |
| ----------------- | ------------------------------------- | -------------------------------- |
| `id`              | UUID (PK)                             |                                  |
| `organization_id` | UUID → `organizations` (type=company) |                                  |
| `module_key`      | text                                  | referencia uma chave do registry |
| `granted_at`      | timestamptz                           |                                  |
| `granted_by`      | UUID → `users`                        | quem (platform_admin) liberou    |

Único por `(organization_id, module_key)`. **Presença da linha = habilitado. Ausência =
negado.** Não há coluna booleana — desligar é apagar (ou expirar, se um dia precisar de
histórico; fora de escopo agora).

## Guard

`require_module("refeicoes")` — dependency (exposta via `core`) que 403 se a `current_organization`
(type=company) não tiver a linha de entitlement. Todo endpoint de um módulo de negócio o
aplica; compõe com `require_permission` (spec 04):

```python
# router montado sob /api/organizacoes/{orgId}/refeicoes
@router.post("/tickets", dependencies=[Depends(require_module("refeicoes")),
                                       Depends(require_permission("catalog.write"))])
```

## Endpoints

Gestão de entitlement (só `platform_admin`):

| Método   | Rota                                        | Ação                                                 |
| -------- | ------------------------------------------- | ---------------------------------------------------- |
| `GET`    | `/api/organizacoes/{orgId}/modulos`         | módulos habilitados da Empresa + catálogo disponível |
| `PUT`    | `/api/organizacoes/{orgId}/modulos/{chave}` | habilita (idempotente)                               |
| `DELETE` | `/api/organizacoes/{orgId}/modulos/{chave}` | desabilita                                           |

Contexto do usuário — `GET /api/organizacoes/{orgId}/me` (spec 04) inclui os módulos
habilitados da organização, pra casca do frontend montar navegação:

```json
"modules": ["refeicoes"]
```

## Contrato do app de negócio (o que "plugar" significa)

Um módulo de negócio, pra existir no superapp, precisa:

1. registrar um `ModuleDescriptor` (chave, personas, permissões, nav);
2. montar rotas sob `/api/organizacoes/{orgId}/<chave>/*`, todas atrás de `require_module(<chave>)`;
3. escopar todo dado por `organization_id` via o helper tenant-scoped (spec 03);
4. declarar suas permissões e checá-las com `require_permission` (spec 04);
5. depender **só** de `core` e dos contracts do kernel — nunca de outro módulo de negócio.

Cumprido isso, adicionar Refeições ou Carro não toca no núcleo.

## Critérios de aceite

1. Endpoint de um módulo responde 403 pra Empresa sem entitlement, mesmo com papel/permissão
   corretos — a negação é do backend, não do frontend.
2. `PUT` do entitlement é idempotente; `DELETE` volta a negar.
3. `GET /api/organizacoes/{orgId}/me` lista exatamente os módulos habilitados da organização.
4. Registrar um módulo novo no `ModuleRegistry` não exige mudança em `core` além do descritor
   e de uma linha em `mount_routes`.
5. Só `platform_admin` altera entitlement; qualquer outro papel recebe 403.

## Como ficou

Os cinco critérios batem e foram observados rodando contra o Postgres real, pela stack do
compose (nginx → backend), incluindo os 401 e 403. O que a implementação decidiu e a spec não
previa:

- **`require_module` não foi pro `core/authz`, ganhou pacote próprio (`core/modules/`) — a
  previsão da spec 04 não valeu.** O motivo raso é ciclo de import (`mount_module` precisa do
  guard, o guard precisa da chave do registry). O motivo de verdade é que **a pergunta é
  outra**: `require_permission` pergunta quem é o usuário e afrouxa pra `platform_admin`;
  `require_module` pergunta o que o _tenant_ comprou e **não afrouxa pra ninguém**. Deixar os
  dois no mesmo pacote convidaria alguém a "consertar" essa assimetria. Verificado rodando: um
  `platform_admin` leva **403** num módulo que a Empresa não contratou — entitlement é fato
  comercial, não privilégio, e a Widelab não abre por dentro o que não vendeu.
- **O `access` chegou a quatro linhas no `mount_routes`, e a `04` errou ao chamar três de
  "teto".** O entitlement é um quarto eixo de kernel (`ModuleEntitlementReader`), e ele não
  cabia em nenhuma das três portas existentes. Agora o teto é real e por um motivo melhor do
  que contagem: os eixos são os que o kernel expõe, e não há um quinto desenhado. O que a `04`
  queria dizer segue de pé e foi provado — **app de negócio tem uma linha só**.
- **A "uma linha" virou `mount_module(api, descritor)`, que faz os três itens do contrato de
  uma vez.** A spec pede que o módulo registre o descritor, monte rotas sob
  `/api/organizacoes/{orgId}/<chave>/*` e ponha `require_module` em todas. Escrito assim, dois
  desses três seriam disciplina — dava pra esquecer o guard numa rota nova, e o 403 sumiria sem
  ninguém notar. O helper faz o prefixo e o guard: sair do contrato exigiria não usá-lo. O
  `require_module(chave)` avulso do exemplo da spec continua exportado e funcionando, pra quem
  quiser as duas negações explícitas na rota.
- **`ModuleDescriptor.permissions` hoje não liga em lugar nenhum — é o furo que a spec não
  viu, e ele é da fase 2.** Um módulo declara `permissions=["catalog.write"]`, mas **não existe
  mecanismo que ligue uma permissão de módulo a um papel**: quem decide quem tem o quê é
  `PERMISSIONS_BY_ROLE`, que é do `access`, e módulo não importa módulo. Então o campo é
  declaração/catálogo, e um `require_permission("catalog.write")` hoje negaria todo mundo, pra
  sempre. Não inventei o mecanismo aqui porque ele muda a forma do descritor (precisaria
  declarar *papel*→permissões, e a spec fixa uma lista plana) e porque a decisão pede um
  declarante real pra ser testada. **Quem fizer Refeições esbarra nisto no primeiro endpoint** —
  provavelmente o descritor passa a declarar papel→permissões e o `PermissionReader` soma os
  descritores do registry ao mapa do kernel. Ganha spec própria. O que **está** provado é que a
  composição funciona: o módulo de fumaça exigiu `require_module` + `require_permission` com uma
  capability de kernel e negou certo.
- **`refeicoes` e `frota` moram em `src/api/modules.py`, e sem `permissions`.** A spec os quer
  "apenas como chaves registradas", mas um descritor pertence ao módulo que descreve — e o
  módulo não existe. Pôr no `core` seria dar ao `core` um catálogo (o erro que a `04` evitou com
  `Permission`); criar `modules/refeicoes/` seria fingir um módulo. Foram pro ponto de
  composição, que não é `core` e não finge nada, com o caminho de saída escrito no topo do
  arquivo. Sem `permissions` porque `catalog.write` e `invoices.approve_hr` são exemplos da
  spec, não decisões tomadas — chutá-las seria fazer fase 2 num placeholder.
- **`GET /modulos` ficou só pra `platform_admin`, como as outras duas linhas da tabela.** A
  spec põe a rota sob o título "Gestão de entitlement (só `platform_admin`)" e é o que ficou:
  um `company_admin` leva 403 ali. Ele não fica sem resposta — o `/me` já lhe diz o que a
  Empresa tem. A diferença é o **catálogo**: "o que dá pra comprar" é tela de quem vende. Se um
  dia a Empresa puder ver a vitrine, é uma decisão de produto, não um ajuste de guard.
- **As permissões novas são `modules.read`/`modules.write`, e o `modules.write` é o simétrico
  do `agreements.write` da spec 03.** Lá, a plataforma não assina contrato no lugar do cliente;
  aqui, o cliente não se vende módulo sozinho. Só `platform_admin` as tem, e o critério 5 cai
  fora do guard genérico sem um `if` de papel na rota: o `SqlAlchemyMembershipReader` já soma as
  permissões de plataforma em qualquer `orgId`. Verificado: `company_admin` e `hr` levam 403 no
  `GET`, no `PUT` e no `DELETE`; sem sessão é 401.
- **A regra da chave desconhecida é a única desta tabela sem rede no banco.** Todo o resto tem
  enforcement estrutural — inclusive "só Empresa contrata módulo", que é FK composta contra
  `organizations(id, type)` com o tipo fixado em coluna gerada, o mesmo truque do convênio.
  Verificado por `psql`, por fora da aplicação: dar entitlement a um Parceiro viola a FK, e
  trocar o `type` de uma Empresa com módulo ligado é bloqueado (isolado numa Empresa **sem**
  convênio, senão o bloqueio viria da FK da spec 03). Mas `module_key` não tem FK: o registry é
  **código**, e um CHECK não o enxerga. Uma tabela `modules` espelhando o registry seria uma
  segunda fonte da verdade, semeada por migration a cada módulo novo — exatamente o "sem deploy"
  que esta spec existe pra ter. Então a chave desconhecida é 422 da aplicação, e só.
- **`DELETE` é idempotente (204 sempre) e não confere o registry.** Idempotente porque o
  `DELETE` afirma um estado ("este módulo não está habilitado aqui") e afirmá-lo duas vezes não
  é erro — mesma lógica do `PUT`, que a spec já pedia. Não confere o registry de propósito: no
  dia em que um módulo for aposentado do código, as linhas dele continuam no banco, e recusar o
  `DELETE` de uma chave desconhecida trancaria a única porta que limpa o que sobrou. Ligar exige
  que o módulo exista; desligar, não.
- **`granted_by` não cascateia.** Apagar quem liberou um módulo é bloqueado pelo banco.
  Cascatear apagaria a venda junto com o funcionário que a registrou; anular exigiria a coluna
  nullable, e "alguém, não sei quem" é justamente o que ela existe pra não dizer. A FK vive só
  na migration, como a de `memberships.user_id` — e herda a mesma dívida: um `--autogenerate`
  futuro vai propor dropá-la, e há um comentário na migration mandando recusar.
- **Como o Parceiro alcança um módulo continua em aberto, e é da fase 2.** `require_module`
  nega toda organização que não é Empresa, que é o que a spec diz ("`current_organization`
  (type=company)"). Mas o descritor de Refeições lista `partner` nas personas: um restaurante
  vai precisar abrir alguma tela. Ele não tem entitlement próprio — pela FK, não pode ter — e o
  caminho provável é o convênio (o Parceiro alcança o módulo _da Empresa_ que ele atende). Isso
  é desenho de produto do primeiro app de negócio, não desta spec, então ficou negado por
  padrão em vez de adivinhado.
- **`/me` de organização que não é Empresa devolve `modules: []`**, e agora isso quer dizer o
  que diz. A `04` recusou devolver `[]` porque na época significaria "entitlement não existe";
  hoje significa "esta organização não contratou nada", que é verdade tanto pro Parceiro quanto
  pra plataforma.
- **`modules` é da organização, não da pessoa** — o `/me` do `company_admin` e o do `hr` na
  mesma Acme devolvem a mesma lista, e o que os separa é `persona`/`permissions`. Verificado. É
  a casca que cruza os dois eixos: aparece no menu o que é módulo do tenant **e** permissão de
  quem olha.
- **Os critérios 1 e 4 foram verificados com um módulo de negócio descartável de verdade**, não
  por leitura — mesma receita da `04`. Um `modules/smoke/` que importava **só** `src.core.authz`,
  `src.core.modules` e `src.core.tenancy`, ligado por **uma linha** em `mount_routes` e **zero**
  mudança no `core`. Rodando, na ordem: 403 pro `company_admin` com papel e permissão corretos e
  sem entitlement (critério 1, com a mensagem "Esta organização não tem este módulo habilitado");
  `PUT` do entitlement → 200 pro mesmo `company_admin`; 403 pro `hr`, que tem o módulo e não tem
  a capability; 401 sem sessão; `DELETE` → 403 de novo (critério 2). Apagado depois, e o 404
  confirmado.
- **Sem testes automatizados** — o backend segue sem framework de teste e esta spec não cita
  testes; a verificação foi por `curl` e `psql`. **A dívida que as specs 03 e 04 registraram
  segue crescendo**: o `PUT` idempotente, o 403 sem entitlement e o "só Empresa contrata" são
  exatamente o que um teste barato protegeria — e agora eles guardam uma regra _comercial_, onde
  um erro não trava a tela, só entrega de graça o que não foi vendido. Uma spec de infra de
  teste (`pytest` + Postgres efêmero) continua sendo o próximo candidato óbvio, e o argumento
  pra ela ficou mais caro de ignorar.
