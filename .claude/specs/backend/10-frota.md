# 10 — Frota (veículos, condutores e registro de uso)

**Depende de:** `backend/09-capabilities-de-modulo.md` (sem ele, `require_permission` de
capability de módulo nega todo mundo), `backend/05-modulos-e-entitlements.md` (o descritor, o
`mount_module`, o `require_module`), `backend/04-membros-e-autorizacao.md` (papéis e persona),
`backend/07-testes.md` (a suíte que os critérios estendem).
**Entrega:** o módulo `frota` — o **primeiro app de negócio** do superapp. Cadastro de veículos e
condutores, registro de uso e o relatório de quilometragem, plugados por uma linha em
`mount_routes` e **zero** mudança em `core`.

## Objetivo

Substituir a folha de papel presa na portaria: quem pegou qual carro, quando saiu, quando voltou
e com quantos quilômetros. O módulo responde três perguntas — *onde está cada carro*, *quem
rodou o quê no mês*, e *quantos quilômetros cada veículo andou* — e é a prova de que o contrato
de plugagem da `05` sustenta um app de negócio de verdade.

## Fora de escopo

- **Reserva/agendamento.** Decidido **não** fazer. O sistema registra o que **aconteceu**, não o
  que vai acontecer. Reserva traria conflito de agenda, aprovação, fila de espera e cancelamento
  — um produto inteiro em cima de um domínio que hoje é uma planilha. Se fizer falta, é spec
  própria, e o modelo desta spec não a impede.
- **Registro obrigatoriamente em tempo real.** Decidido **não** exigir. Lançamento **retroativo é
  cidadão de primeira classe** — ver "Retroativo" abaixo. Não haverá campo que só o relógio do
  servidor preencha.
- **Combustível, manutenção, multas, seguro e custo por km.** São os pedidos óbvios seguintes e
  nenhum deles cabe aqui: cada um traz nota fiscal, fornecedor e rateio — dinheiro, que é o eixo
  de Refeições, não deste. Ganham spec própria depois que o registro de uso estiver rodando.
- **Alerta de vencimento de CNH.** A validade é **dado** (fica em `drivers`), mas notificar quem
  está pra vencer é compliance com regra de antecedência, canal e reincidência. Spec própria.
- **Checklist de avaria, foto de painel e telemetria/GPS.** Captura de mídia e integração
  externa; nada disto é pré-requisito pra aposentar o papel.
- **Frontend.** As telas são `frontend/07`, como a `06` foi backend e frontend separados. Todos
  os critérios abaixo são observáveis por requisição, sem esperar UI.
- **Parceiro.** Frota é módulo de Empresa; o descritor não lista `partner` nas personas. O
  problema em aberto desde a `05` — como um Parceiro alcança um módulo — **não** é resolvido nem
  esbarrado aqui; ele nasce com Refeições.

## O módulo

`src/modules/frota/`, em camadas (`domain` → `application` → `adapters`), importando **só**
`src.core` — nunca `auth` nem `access`. O descritor sai de `src/api/modules.py` e vai pra
`src/modules/frota/module.py`, que é o caminho de saída escrito no topo daquele arquivo desde a
`05`; `mount_routes` troca a linha do placeholder por `mount_module(api, FROTA)`.

```python
FROTA = ModuleDescriptor(
    key="frota",
    name="Frota",
    personas=["company_admin", "collaborator"],
    grants={...},          # tabela abaixo
    nav=ModuleNav(label="Frota", path="/frota"),
    router=router,
)
```

### Capabilities e quem as recebe

Namespaced pela chave, como a `09` exige:

| Capability | O que autoriza |
|---|---|
| `frota.vehicles.read` | ver a lista de veículos |
| `frota.vehicles.write` | cadastrar e editar veículo |
| `frota.drivers.read` | ver a lista de condutores |
| `frota.drivers.write` | cadastrar e editar condutor |
| `frota.usages.read` | ver **todos** os registros de uso da Empresa |
| `frota.usages.write` | lançar, corrigir e apagar uso de **qualquer** condutor |
| `frota.usages.write_own` | lançar e encerrar uso em que o condutor é **você** |

| Papel | Recebe |
|---|---|
| `company_admin` | todas |
| `manager` | todas |
| `collaborator` | `frota.vehicles.read`, `frota.usages.write_own` |
| `hr`, `finance` | nenhuma |

`manager` recebe tudo porque é ele o **gestor de frota** — e é aqui que o papel finalmente ganha
capability. A `04` o deixou com `frozenset()` dizendo que o que ele faz são capabilities de
módulo; esta spec é a primeira a cumprir essa promessa.

`hr` e `finance` saem sem nada, e é decisão: RH cuida de gente, e o custo da frota está fora de
escopo — quando entrar, `finance` ganha leitura. Um `company_admin` que precise ver frota já vê,
porque tem todas.

`collaborator` recebe `vehicles.read` porque **precisa escolher o carro** pra lançar a viagem —
sem isso o formulário não tem o que oferecer. Não recebe `drivers.read`: ele lança em nome de si
mesmo, e a lista de condutores da Empresa não é dele.

## Retroativo é o caso normal, e isso muda o desenho

A premissa honesta é que ninguém vai abrir o app na portaria: a viagem é lançada depois, às vezes
dias depois, às vezes por outra pessoa. Três consequências, e as três são decisões:

1. **`started_at` e `ended_at` são digitados**, nunca `now()` do servidor. Não existe rota
   "iniciar viagem agora" que preencha a hora sozinha.
2. **Data futura é recusada** (`started_at > now()` → 422). Retroativo é pra trás; sem esse
   limite, "retroativo" vira "qualquer data" e some a última âncora de sanidade. **A validação é
   da aplicação, não do banco**: um `CHECK (started_at <= now())` é rejeitado pelo Postgres —
   `now()` não é imutável e não entra em `CHECK`. É a única regra desta spec que o banco não
   consegue impor, e está anotada como tal.
3. **O hodômetro inicial não tem default.** Em tempo real ele seria o final da viagem anterior;
   lançado fora de ordem, não é. Vira campo digitado — ver "Continuidade do hodômetro".

## Schema (migration `0006_frota`)

Três tabelas, todas escopadas por `organization_id` com a **FK composta contra
`organizations(id, type)`** e o tipo fixado em coluna gerada — o mesmo truque de
`module_entitlements` (`05`), aqui garantindo que **só Empresa tem frota**.

A migration cria a extensão **`btree_gist`** (`CREATE EXTENSION IF NOT EXISTS btree_gist`), sem a
qual a constraint de exclusão de `vehicle_usages` não existe.

### `vehicles`

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | `uuid` PK | `uuid7`, como o resto do projeto |
| `organization_id` | `uuid` | + `organization_type` gerada + FK composta |
| `plate` | `text` | a placa, normalizada em maiúsculas pela aplicação |
| `brand`, `model` | `text` | marca e modelo |
| `model_year` | `int \| null` | |
| `initial_odometer` | `int` | o hodômetro no dia do cadastro |
| `status` | `vehicle_status` | `active` / `maintenance` / `inactive` |
| `created_at` | `timestamptz` | |

- `UNIQUE (organization_id, plate)` — duas Empresas podem ter a mesma placa (frota terceirizada,
  carro vendido de uma pra outra); a mesma Empresa, não.
- `UNIQUE (id, organization_id)` — redundante como chave, mas é o alvo da FK composta de
  `vehicle_usages`. Mesmo papel do `uq_organizations_id_type` na `03`.
- **Não há coluna de hodômetro atual.** Ele é derivado (`initial_odometer` ou o maior
  `end_odometer` registrado); guardá-lo seria uma segunda fonte da verdade pra divergir da
  primeira no primeiro lançamento retroativo fora de ordem.

### `drivers`

Condutor é **entidade própria, não um `membership`** — decisão de produto tomada com o usuário. O
motorista terceirizado, o prestador e o entregador dirigem e nunca vão logar; exigir login de
todo condutor forçaria cadastrar usuário-fantasma pra gente que não usa o sistema, e o resultado
seria dado sujo. Quem **também** é usuário ganha o vínculo opcional abaixo e passa a poder lançar
a própria viagem.

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | `uuid` PK | |
| `organization_id` | `uuid` | + `organization_type` gerada + FK composta |
| `name` | `text` | |
| `user_id` | `uuid \| null` | o vínculo opcional com quem tem login — ver abaixo |
| `license_number` | `text \| null` | CNH |
| `license_category` | `text \| null` | A, B, AB, D… texto, não enum: as categorias mudam por resolução do Contran e não vale uma migration por mudança de lei |
| `license_expires_at` | `date \| null` | dado, sem alerta (fora de escopo) |
| `status` | `driver_status` | `active` / `inactive` |
| `created_at` | `timestamptz` | |

- `UNIQUE (id, organization_id)` — alvo da FK composta de `vehicle_usages`.
- `UNIQUE (organization_id, user_id)` parcial (`WHERE user_id IS NOT NULL`) — um usuário é no
  máximo um condutor na mesma Empresa, senão "lançar a própria viagem" fica ambíguo.

**`user_id` não tem FK, e é deliberado — este é o primeiro teste do seam de extração.** O
precedente imediato é `Membership.user_id`, que aponta pra `users` com a FK só na migration pra
não fazer `access` importar `auth`. Aqui vai um passo além: **não há FK nenhuma**. Uma FK de um
app de negócio pra tabela do kernel é exatamente o que tornaria `frota` não-destacável — no dia
em que ele tiver schema próprio (`00-visao-geral.md`), essa FK é o que precisaria ser desfeito.
Frota referencia identidade por id opaco e pronto.

O que sustenta a segurança disso é que **um `user_id` obsoleto não vaza nada**: pra alcançar
qualquer rota de frota o chamador já precisa de vínculo ativo na Empresa (`current_organization`)
e do entitlement (`require_module`). Um condutor apontando pra alguém que não é mais membro
simplesmente nunca é alcançado. Frota **não valida** que o `user_id` é membro — validar exigiria
ler `memberships`, que é do `access`, e a alternativa (uma porta nova no `core`) gastaria
privilégio de kernel numa conveniência. Quem escolhe o `user_id` é a tela do gestor, a partir do
`GET .../membros` que a `04` já entrega.

### `vehicle_usages`

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | `uuid` PK | |
| `organization_id` | `uuid` | + `organization_type` gerada + FK composta |
| `vehicle_id` | `uuid` | FK composta `(vehicle_id, organization_id)` → `vehicles(id, organization_id)` |
| `driver_id` | `uuid` | FK composta `(driver_id, organization_id)` → `drivers(id, organization_id)` |
| `started_at` | `timestamptz` | digitado |
| `ended_at` | `timestamptz \| null` | `null` = viagem aberta |
| `start_odometer` | `int` | digitado |
| `end_odometer` | `int \| null` | |
| `purpose` | `text \| null` | destino/finalidade |
| `notes` | `text \| null` | |
| `created_by` | `uuid` | quem lançou; sem FK, mesma regra de `drivers.user_id` |
| `created_at` | `timestamptz` | |

As FKs de veículo e condutor são **compostas com `organization_id`** — não simples. É o que torna
impossível registrar o carro da Empresa A com o motorista da Empresa B: em multi-tenant com banco
compartilhado, uma FK simples aceitaria a mistura, e o vazamento apareceria num relatório meses
depois. Ambas as tabelas são do próprio `frota`, então isto não fura fronteira de módulo nenhuma.

Constraints:

| Constraint | Regra |
|---|---|
| `ck_vehicle_usages_period` | `ended_at IS NULL OR ended_at > started_at` |
| `ck_vehicle_usages_odometer` | `end_odometer IS NULL OR end_odometer >= start_odometer` |
| `ck_vehicle_usages_closed_together` | `(ended_at IS NULL) = (end_odometer IS NULL)` |
| `ex_vehicle_usages_no_overlap` | `EXCLUDE USING gist (vehicle_id WITH =, tstzrange(started_at, ended_at) WITH &&)` |

**A constraint de exclusão é a peça central desta spec.** Com registro em tempo real bastaria um
índice único parcial ("um veículo tem no máximo uma viagem aberta"); com lançamento retroativo,
alguém digita na sexta a viagem de terça e nada impediria que ela **se sobrepusesse** a outra já
registrada no mesmo carro — o veículo em dois lugares ao mesmo tempo, e o relatório de km errado
sem ninguém notar. A exclusão cobre os dois modos de uma vez, e de quebra entrega o índice
parcial de graça: `tstzrange(started_at, NULL)` é **sem limite superior**, então uma viagem
aberta colide com qualquer outra do mesmo veículo — inclusive uma segunda viagem aberta.

`ck_vehicle_usages_closed_together` existe pra encerrar ser **atômico**: uma viagem com hora de
volta e sem hodômetro final é meia-linha que estraga o relatório e ninguém repara. Ou fecha
inteira, ou não fechou.

### Continuidade do hodômetro: regra de aviso, não de bloqueio

O km inicial de uma viagem **não** precisa bater com o km final da anterior, e o sistema **não**
recusa a divergência. Painel trocado, carro que rodou sem registro e erro de digitação corrigido
depois são reais demais pra travar o lançamento — travar faria o usuário inventar um número, que
é pior que o buraco. A divergência aparece no relatório como lacuna; não vira 422.

## Rotas

Todas sob `/api/organizacoes/{orgId}/frota/*`, penduradas por `mount_module` — o prefixo e o
`require_module` não são disciplina do módulo (`05`).

| Rota | Capability |
|---|---|
| `GET /veiculos` | `frota.vehicles.read` |
| `POST /veiculos` | `frota.vehicles.write` |
| `GET /veiculos/{id}` | `frota.vehicles.read` |
| `PATCH /veiculos/{id}` | `frota.vehicles.write` |
| `GET /condutores` | `frota.drivers.read` |
| `POST /condutores` | `frota.drivers.write` |
| `GET /condutores/{id}` | `frota.drivers.read` |
| `PATCH /condutores/{id}` | `frota.drivers.write` |
| `GET /usos` | — escopo por capability, ver abaixo |
| `POST /usos` | `frota.usages.write` **ou** `write_own` |
| `PATCH /usos/{id}` | `frota.usages.write` **ou** `write_own` (só o próprio) |
| `POST /usos/{id}/encerrar` | `frota.usages.write` **ou** `write_own` (só o próprio) |
| `DELETE /usos/{id}` | `frota.usages.write` |
| `GET /relatorios/quilometragem` | `frota.usages.read` |

Listagens paginadas com o `PageResponse[...]` que a `03` fixou. **Não há `DELETE` de veículo nem
de condutor** — os dois viram `inactive` pelo `PATCH`. Apagar levaria junto o histórico que é o
produto; um carro vendido some da lista de escolha e continua nos relatórios de quando rodava.

### `GET /usos` — o escopo é dado, não porta

A rota exige só o módulo; **o que ela devolve depende da capability**: quem tem
`frota.usages.read` vê os usos de toda a Empresa; quem não tem vê **só os do condutor vinculado
ao próprio `user_id`** (lista vazia, se não houver condutor vinculado). Uma rota só, e não duas:
duplicar a rota duplicaria paginação, filtros e ordenação pra mudar uma cláusula `WHERE`. Filtros
aceitos: `?veiculo=`, `?condutor=`, `?de=`, `?ate=`, `?abertos=true`.

### `POST /usos/{id}/encerrar` — rota própria, e não um `PATCH`

Encerrar recebe `ended_at` + `end_odometer` **juntos** e é o gesto mais frequente do módulo
inteiro — a única coisa que o Colaborador faz. Rota própria porque a transição tem validação
própria (os dois campos, a constraint `closed_together`) e porque encerrar uma viagem já
encerrada é **409**, enquanto corrigir uma viagem encerrada é `PATCH` e é legítimo. Espremer as
duas num `PATCH` faria "fechar" e "corrigir" indistinguíveis no log e na permissão.

### `write_own` — o que "próprio" quer dizer

Quem tem só `frota.usages.write_own` pode agir **exclusivamente** sobre uso cujo `driver_id`
aponta pro condutor vinculado ao seu `user_id`, e **não pode** criar ou mudar um uso pra outro
condutor (`driver_id` diferente do seu → 403). Um `collaborator` sem condutor vinculado recebe
**422** ao tentar lançar: ele não é condutor cadastrado, e a mensagem diz isso.

`DELETE` fica **fora** do `write_own` de propósito: o registro é a matéria-prima do relatório, e
quem apaga a própria viagem apaga a evidência. Corrigir, sim (`PATCH`); sumir, é ato do gestor.

### `GET /relatorios/quilometragem`

O relatório que justifica o modelo inteiro — a pergunta que a folha de papel existe pra
responder. Recebe `?de=&ate=` (obrigatórios) e agrupa por veículo ou por condutor
(`?agrupar_por=veiculo|condutor`, default `veiculo`), somando `end_odometer - start_odometer` dos
usos **encerrados** no período. Usos abertos entram como contagem à parte, nunca como zero km —
"não sei" e "não rodou" não podem virar o mesmo número.

## Regras que a aplicação impõe (o banco não alcança)

| Regra | Resposta |
|---|---|
| `started_at` no futuro | 422 (`CHECK` com `now()` é impossível) |
| veículo `inactive`/`maintenance` recebendo uso novo | 422 (um `CHECK` não enxerga outra tabela) |
| condutor `inactive` recebendo uso novo | 422 |
| `driver_id` de outro condutor com só `write_own` | 403 |
| lançar sem condutor vinculado com só `write_own` | 422 |
| placa duplicada na mesma Empresa | 409 (o `UNIQUE` é quem garante) |
| sobreposição de período no mesmo veículo | 409, traduzido da violação de exclusão |

O 409 da sobreposição é traduzido de `IntegrityError`, e **não** verificado com um `SELECT`
antes: entre a leitura e a escrita cabe outro lançamento, e a corrida é justamente o caso que a
constraint existe pra pegar. Mesma decisão do `UPDATE ... WHERE status = 'pending'` da `06`.

## Testes — na mesma entrega

- **`tests/unit/frota/`** (sem Docker) — o mapa de `grants` do descritor, a normalização da
  placa, a regra de data futura e o agrupamento do relatório.
- **`tests/integration/frota/`** — as rotas contra Postgres real, com a fixture `como(role=…,
  org=…)` da `07`. As invariantes de banco (exclusão, `closed_together`, FK composta cruzando
  tenant) entram com **`INSERT` direto por fora da aplicação**, como a `05` verificou o "só
  Empresa contrata" — o que se está afirmando é que o banco impede, não que a rota valida.

## Critérios de aceite

1. `mount_routes` ganha **`mount_module(api, FROTA)`** e nada mais; `src/modules/frota/` não
   importa `src.modules.auth` nem `src.modules.access`, e `src/core` não muda em nenhuma linha —
   verificável por leitura de import e por `git diff` em `src/core`.
2. Numa Empresa **sem** o entitlement `frota`, um `company_admin` recebe **403** em qualquer rota
   do módulo. Ligado o flag (`PUT .../modulos/frota`), o mesmo request responde 200 — sem deploy.
3. Um `manager` cadastra veículo e condutor, lança um uso e o encerra, e um `collaborator` recebe
   **403** no `POST /veiculos` e no `POST /condutores` — as capabilities do descritor chegaram
   aos papéis pelo mecanismo da `09`, sem nenhuma linha em `PERMISSIONS_BY_ROLE`.
4. Um `collaborator` vinculado a um condutor lança um uso **em seu próprio nome** (201) e recebe
   **403** ao lançar com o `driver_id` de outro condutor. Sem condutor vinculado, recebe **422**.
5. `GET /usos` como `manager` lista os usos de toda a Empresa; como `collaborator`, lista **só**
   os do seu condutor — e um uso de outro condutor não aparece.
6. Lançar um uso cujo período **se sobrepõe** a outro do mesmo veículo responde **409**, inclusive
   quando o uso existente está **aberto** (`ended_at IS NULL`). O mesmo período em **outro**
   veículo é aceito (201).
7. Um `INSERT` direto no banco de um `vehicle_usages` cruzando tenant (veículo da Empresa A,
   condutor da Empresa B) **viola a FK composta**; e um `INSERT` com `ended_at` preenchido e
   `end_odometer` nulo viola `ck_vehicle_usages_closed_together`. Os dois falham por fora da
   aplicação.
8. `POST /usos/{id}/encerrar` grava `ended_at` + `end_odometer` e responde 200; repetido no mesmo
   uso, responde **409**. `PATCH` sobre um uso já encerrado segue aceito (correção).
9. `POST /usos` com `started_at` no futuro responde **422**; com veículo `inactive` ou condutor
   `inactive`, **422**. `POST /veiculos` com placa já existente na Empresa responde **409**, e a
   mesma placa em **outra** Empresa é aceita.
10. `DELETE /usos/{id}` responde **403** pra quem tem só `write_own` (mesmo sobre o próprio uso) e
    **204** pro `manager`. Não existe `DELETE` de veículo nem de condutor (**405**/404); desativar
    é `PATCH status=inactive`, e o veículo desativado continua aparecendo nos relatórios do
    período em que rodou.
11. `GET /relatorios/quilometragem?de=&ate=` soma `end_odometer - start_odometer` dos usos
    encerrados no período, agrupado por veículo e por condutor, e reporta os usos **abertos** como
    contagem separada — nunca somados como zero.
12. Um uso lançado retroativamente (`started_at` de dias atrás, com `ended_at` também no passado)
    é aceito com 201, e nenhum campo de data foi preenchido pelo relógio do servidor.
