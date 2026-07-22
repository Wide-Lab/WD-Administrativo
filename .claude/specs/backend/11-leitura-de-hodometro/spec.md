# 11 — Leitura de hodômetro por foto

**Estado:** ✅ implementada (2026-07-22) — 11 dos 12 critérios observados rodando; o **11 não pôde
ser verificado** (as fotos do spike não estão no repo e não há chave de fornecedor configurada).
317 testes. Ver [`como-ficou.md`](./como-ficou.md).
**Depende de:** `backend/10-frota/spec.md` (as tabelas, as capabilities e o `AnyUsageWriter`),
`backend/05-modulos-e-entitlements/spec.md` (o `mount_module` e o `require_module`),
`backend/07-testes/spec.md` (a suíte que os critérios estendem).
**Entrega:** a porta de armazenamento de arquivos no `core`, a porta de leitura de hodômetro no
`frota` com adaptador multimodal, o hodômetro atual do veículo, e as rotas que fotografam um painel
e devolvem o número — guardando a foto como evidência.

## Objetivo

Tirar o hodômetro do teclado. Hoje quem lança uma viagem digita cinco ou seis dígitos que está
lendo do painel a um metro de distância, e erra — e o erro só aparece no relatório de
quilometragem, meses depois, como uma lacuna que ninguém consegue mais explicar. A pessoa
fotografa o painel, o número vem preenchido, ela confirma. A foto fica guardada, então a
quilometragem deixa de ser afirmação e passa a ser afirmação **com prova**.

## Fora de escopo

- **Ler qualquer outro campo da foto.** Só o hodômetro. Placa, condutor e instante ficam de fora:
  placa e condutor exigiriam outra foto e outro problema (reconhecer caractere de placa é domínio
  próprio), e o instante por EXIF foi **decidido fora** pelo Kauan em 2026-07-22 — a foto tirada
  da galeria carrega a data de quando foi tirada, e explicar isso ao usuário custa mais que o
  campo economiza. `started_at` e `ended_at` seguem digitados, como a `10` decidiu.
- **Recorte guiado na tela.** Foi cogitado e **descartado com medição** — ver "A decisão do
  motor". O recorte existia pra viabilizar o caminho sem IA; sem ele no desenho, o recorte vira um
  gesto a mais por viagem sem nada em troca, porque o motor escolhido lê o painel inteiro e
  distingue o total do parcial sozinho.
- **Bloquear lançamento por hodômetro implausível.** A `10` decidiu que continuidade de hodômetro
  é **aviso, não bloqueio** ("travar faria o usuário inventar um número, que é pior que o
  buraco"), e essa decisão não muda por existir uma foto. O `plausivel` desta spec é um sinal pra
  tela, nunca um 422.
- **Fila/processamento assíncrono.** A leitura é síncrona dentro da requisição. Assíncrono exigiria
  worker, fila e polling na tela — infra que o projeto não tem, pra economizar segundos num gesto
  que a pessoa já está esperando terminar.
- **Reconhecer que a foto é do carro certo.** O modelo lê um painel, não confere se o painel é
  daquele veículo. Não há como fazê-lo sem telemetria, e fingir que há seria pior que não ter.
- **Frontend.** As telas são `frontend/10`. Todo critério abaixo é observável por requisição.

## A decisão do motor: o caminho sem IA morreu com evidência

A pergunta que abriu esta spec foi do Kauan: *"como é só ler um número, talvez seja possível
implementar sem IA"*. Foi medida antes de ser respondida, num bake-off em
`.claude/spikes/hodometro-ocr/` (2026-07-22), e a resposta é **não**.

O que se mediu, com Tesseract em 5 pré-processamentos × 3 modos de segmentação, e com a
`ssd.traineddata` (treinada em display de sete segmentos) além da `eng` — porque condenar o
caminho sem IA sem lhe dar a `traineddata` do próprio caso de uso seria espantalho:

| | `eng` | `ssd` |
| --- | :---: | :---: |
| acerto exato | 0 de 6 | 0 de 6 |
| errado **com confiança** | 0% | 83% |
| **valor correto nunca produzido** | **100%** | **100%** |

A linha que decide é a última. Em toda foto em que algum número saiu, o valor certo **não estava
entre os candidatos** — nem no mais confiante, nem em nenhum outro. Isso é diferente de "errou a
escolha": errar a escolha é problema de heurística, e heurística se conserta com votação ou
desempate. Não produzir a resposta em ~38 configurações é problema de leitura, e nenhuma
heurística resgata um número que nunca foi lido. A `traineddata` especializada ainda **piorou** o
que mais importa: o `ssd` nunca se abstém, então erra calado.

Duas ressalvas ficam registradas porque a honestidade delas importa mais que a conclusão:

1. **A amostra é pequena e enviesada.** Seis fotos, das quais só uma em resolução usável
   (510×213); as outras eram miniaturas de 71×30 a 245×167, e a rodada delas foi descartada. Fotos
   da internet são mais fáceis que fotos de estacionamento — foram tiradas *pra mostrar* o
   hodômetro. Isso torna o resultado assimétrico, e é assim que ele foi lido: falhar no fácil é
   conclusivo, acertar no fácil não seria.
2. **O lado multimodal nunca foi medido.** O Kauan decidiu (2026-07-22) seguir para IA sem rodar
   essa metade, e a decisão é dele. Então esta spec **não promete taxa de acerto** — e é por isso
   que o critério de aceite 11 exige leitura correta sobre fotos reais antes de a entrega fechar.
   Se o motor não entregar, o que muda é o adaptador, não o desenho.

**O motor é OpenAI** (decisão do Kauan, 2026-07-22), atrás de uma porta. O que faz o multimodal
ganhar não é ler dígito melhor — é resolver o problema que o pipeline clássico não resolve de
jeito nenhum: **qual dos números do painel é o hodômetro**. Velocímetro, relógio, temperatura e o
hodômetro parcial ficam a centímetros do total e têm a mesma cara; o `ssd` ofereceu 4,7 candidatos
por foto em imagens que continham **um** número. E o multimodal sabe dizer "não consegui",
que é a resposta que o Tesseract estruturalmente não tem.

## `core/storage` — a porta de arquivo, no núcleo

**A porta nasce no `core`, dentro da spec do primeiro cliente** — exatamente como
`core/notifications/` nasceu na `backend/06`. É a mesma categoria: infra, não tabela de módulo.
Então ela **não ganha linha em `mount_routes`** e não é um dos cinco registros de porta de kernel;
o `core` a resolve sozinho a partir da config, como faz com o `EmailSender`.

Nasce em `core/` e não em `modules/frota/` porque Refeições vai querer anexo de nota fiscal, e
duas histórias de arquivo no mesmo produto é como a dívida de `PageResponse` começou (`00-visao-geral.md`).
Aqui o custo de acertar de primeira é uma pasta.

```python
class ObjectStorage(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> tuple[bytes, str]: ...   # conteúdo, content_type
    async def delete(self, key: str) -> None: ...
```

| Adaptador | Quando | Por quê |
| --- | --- | --- |
| `LocalDirectoryStorage` | **default**, dev e testes | O gêmeo do `LoggingEmailSender`: `docker compose up db` continua subindo sem MinIO, e a suíte roda contra `tmp_path` sem serviço nenhum. |
| `S3ObjectStorage` | produção | MinIO no compose, API S3. S3-compatível e não S3: o produto é vendido self-hosted, e amarrar a AWS contradiz isso. |

Config: `STORAGE_BACKEND=local|s3`, `STORAGE_LOCAL_DIR`, `S3_ENDPOINT_URL`, `S3_BUCKET`,
`S3_ACCESS_KEY`, `S3_SECRET_KEY`. O `docker-compose.yml` ganha o serviço `minio` e o `nginx` **não**
o expõe — o bucket não é público, e todo byte sai pela API, atrás dos guards.

**A chave sempre começa pelo tenant:** `{organization_id}/frota/hodometro/{uuid7}.jpg`. Não é
segurança (a autorização é das rotas), é operação: apagar um tenant, auditar consumo ou mover uma
Empresa de bucket vira prefixo, não `SELECT`.

**A chave nunca vem do cliente.** Quem a monta é o servidor, e o cliente só conhece o `id` da
leitura. Aceitar chave do cliente seria entregar leitura e escrita arbitrárias no bucket.

## `OdometerReader` — a porta de leitura, no módulo

Esta fica em `src/modules/frota/application/ports/`, **não** no `core`: ler hodômetro é capability
da frota, não infra transversal. Se um dia Refeições quiser ler nota fiscal, o que se compartilha
é o `ObjectStorage`, não este.

```python
@dataclass(frozen=True, slots=True)
class OdometerReading:
    value: int | None          # None = o motor se absteve, e isso é resposta, não falha
    confidence: Confidence     # HIGH | MEDIUM | LOW
    engine: str                # "openai:gpt-4o" — gravado, porque o motor vai trocar
    note: str                  # o que o motor viu; entra no log, nunca na resposta HTTP

class OdometerReader(Protocol):
    async def read(self, image: bytes, content_type: str) -> OdometerReading: ...
```

`value: None` é **resposta de sucesso**, não erro: "não consegui ler" é o comportamento certo
diante de foto tremida, e o que se quer evitar é o palpite confiante que o `ssd` deu em 83% das
vezes. A rota responde 200 com `valor: null`, e a tela pede pra digitar.

`engine` é gravado em cada leitura porque **o motor vai trocar** — de modelo, de fornecedor, ou pra
um local no dia em que compensar. Sem essa coluna, medir a qualidade da leitura em produção depois
de uma troca seria impossível: as duas populações estariam misturadas.

Adaptadores: `OpenAIOdometerReader` (produção) e `StubOdometerReader` (testes, devolve valor
fixo). **A suíte não fala com rede** — é a porta que garante isso, e é o motivo principal de ela
existir.

**Timeout de 15s.** Estourou, a leitura vira `value=None` e a resposta é 200, não 504: o formulário
continua utilizável e a pessoa digita. Um erro do fornecedor não pode bloquear o lançamento da
viagem — o produto é o registro, a leitura é conveniência.

## O hodômetro atual do veículo

`VehicleResponse` ganha **`current_odometer`**, derivado:

```sql
GREATEST(
  v.initial_odometer,
  COALESCE(MAX(u.end_odometer), 0),
  COALESCE(MAX(u.start_odometer), 0)
)
```

**Isto fecha o item que a `frontend/07` pôs fora de escopo** com o nome certo: *"o campo é do
backend e é spec própria"*. Ela recusou derivá-lo na tela a partir de `GET /usos` pra não criar
uma segunda contabilidade de quilometragem no navegador — a mesma dívida do `effective_status` da
`08`. Aqui ele nasce onde devia.

**Derivado, nunca coluna.** O docstring de `Vehicle` já dizia por quê: guardá-lo seria uma segunda
fonte da verdade, pronta pra divergir da primeira no primeiro lançamento retroativo fora de ordem.
Sai por `LEFT JOIN` sobre um agregado, na listagem e no detalhe — **uma query**, não N+1.

`start_odometer` de viagem aberta entra no `GREATEST` porque um carro na rua já rodou: ignorá-lo
faria o prior de um veículo em viagem apontar pra antes da saída.

### O que o prior faz pela leitura

Com ele, a resposta deixa de ser um número solto e vira uma frase conferível: *"li 45.210, o
último registrado foi 45.180, +30 km"*. A tela mostra o delta, e a pessoa confirma num segundo em
vez de reconferir dígito a dígito.

```
plausivel = ultimo_hodometro <= valor <= ultimo_hodometro + 2000
```

Os 2.000 km são o teto de uma viagem única — acima disso é quase certo erro de leitura ou de
digitação, e abaixo de zero o hodômetro andou pra trás. **É sinal, nunca bloqueio**: `plausivel:
false` responde 200 com o número lido, porque a `10` já decidiu que divergência de hodômetro é
aviso. Um carro que rodou 2.100 km numa viagem existe, e recusá-lo faria a pessoa inventar um
número.

## Schema (migration `0007_odometer_readings`)

### `odometer_readings`

| Coluna | Tipo | Nota |
| --- | --- | --- |
| `id` | `uuid` PK | `uuid7` |
| `organization_id` | `uuid` | + `organization_type` gerada + FK composta — só Empresa, como as três da `10` |
| `vehicle_id` | `uuid` | FK composta `(vehicle_id, organization_id)` |
| `storage_key` | `text` | onde a foto está; montada pelo servidor |
| `value_read` | `int \| null` | o que o motor leu; `null` = absteve-se |
| `confidence` | `reading_confidence` | `high` / `medium` / `low` |
| `engine` | `text` | `"openai:gpt-4o"` — ver acima |
| `created_by` | `uuid` | id opaco, **sem FK**, como `drivers.user_id` (`10`) |
| `created_at` | `timestamptz` | |

- `UNIQUE (id, organization_id)` — alvo da FK composta de `vehicle_usages`, mesmo papel que as da `10`.

**A tabela guarda o que a máquina disse, e `vehicle_usages` guarda o que a pessoa confirmou.** Os
dois separados de propósito: a diferença entre eles é a taxa de erro do motor **em produção, nos
carros do cliente** — a medição que o spike não pôde fazer. Sobrescrever `value_read` com a
correção humana apagaria exatamente esse dado.

### `vehicle_usages` ganha duas colunas

| Coluna | Tipo | Nota |
| --- | --- | --- |
| `start_reading_id` | `uuid \| null` | FK composta → `odometer_readings(id, organization_id)` |
| `end_reading_id` | `uuid \| null` | idem |

Nulas porque a foto é **opcional e continua sendo**: quem quiser digitar, digita. Um módulo que
exigisse foto pra lançar viagem teria trocado uma folha de papel por uma catraca.

A referência mora na viagem (e não `usage_id` na leitura) porque a pergunta que o produto faz é
"qual a foto **desta** viagem", e não "esta foto virou o quê". Órfã é leitura que ninguém aponta.

O model novo entra em `migrations/env.py`, senão o `--autogenerate` propõe dropá-lo (`CLAUDE.md`).

**A allowlist do `alembic check` vai de seis para sete.** As duas FKs de `vehicle_usages` para
`odometer_readings` são internas ao `frota` e não contam, mas a `fk_odometer_readings_organization`
**cruza módulo** — como as três equivalentes da `10` — e por isso vive só na migration, fora do
model. Quem for escrever a spec de CI precisa saber que o número mudou: a lista não é fixa, ela
cresce a cada tabela nova de app de negócio, e é o preço combinado do seam de extração.

### Órfãs

Leitura que nunca virou viagem (a pessoa fotografou e fechou o diálogo) é lixo com foto junto.
Purga **oportunista**, na própria rota de leitura: antes de gravar a nova, apaga até **50** leituras
da organização com mais de **24 horas** e sem viagem apontando — linha e objeto.

Oportunista e não agendada porque **o projeto não tem scheduler**, e inventar um pra isso seria
trocar um problema de 50 linhas por um de infra. Fica registrado como o que é: solução modesta,
que vira job no dia em que houver onde pendurá-lo.

## Rotas

Todas sob `/api/organizacoes/{orgId}/frota/*`, penduradas por `mount_module`.

| Rota | Capability |
| --- | --- |
| `POST /veiculos/{id}/hodometro/leituras` | `frota.usages.write` **ou** `write_own` |
| `GET /usos/{id}/hodometro/{saida\|chegada}` | escopo por capability, como `GET /usos` |

**Nenhuma capability nova**, e isso é decisão: ler hodômetro é parte de lançar viagem, e um
`frota.odometer.read` separado poderia ser concedido a quem não pode lançar nada — um direito que
não existe. O guard é o mesmo `AnyUsageWriterDep` do `POST /usos`.

**A leitura é aninhada no veículo** porque sem saber o carro não há prior, e sem prior a resposta é
um número solto. Na tela o veículo já está escolhido acima do campo de hodômetro.

### `POST /veiculos/{id}/hodometro/leituras`

`multipart/form-data`, campo `foto`. Responde **201**:

```json
{
  "id": "01890000-...",
  "valor": 45210,
  "confianca": "alta",
  "plausivel": true,
  "ultimo_hodometro": 45180,
  "delta": 30
}
```

`valor: null` quando o motor se absteve — `confianca: "baixa"`, `plausivel: false`, `delta: null`,
e ainda assim **201 com a foto guardada**: a leitura aconteceu, o resultado é "não sei", e a foto
serve de evidência do mesmo jeito.

| Situação | Resposta |
| --- | --- |
| foto acima de **8 MB** | 413 |
| `content-type` fora de `image/jpeg`, `image/png`, `image/webp` | 415 |
| bytes que não decodificam como imagem, ou acima de **50 MP** decodificados | 422 |
| veículo de outra Empresa, ou inexistente | 404 |
| veículo `inactive` | 422 — não recebe uso novo (`10`), então não há o que fotografar |
| mais de **30 leituras por usuário por hora** | 429 |

O teto de 50 MP é anti-bomba de descompressão: 8 MB de PNG viram gigabytes na memória se o
servidor decodificar sem olhar. Quem valida é Pillow, antes de qualquer coisa tocar o motor.

**HEIC não entra** (415). iPhone fotografa em HEIC, mas o frontend reduz e reencoda pra JPEG antes
de subir (`frontend/10`), então o formato nunca chega aqui — e aceitá-lo custaria `pillow-heif` no
container por um caminho que ninguém percorre.

### `POST /usos` e `POST /usos/{id}/encerrar` ganham a referência

`POST /usos` aceita `leitura_saida_id` e `leitura_chegada_id`; `encerrar` aceita
`leitura_chegada_id`. Todos opcionais. A leitura precisa ser da **mesma organização** e do **mesmo
veículo** do uso, e ainda **não estar** apontada por outra viagem — senão **422**. Sem essas três
conferências, uma foto viraria evidência de duas viagens diferentes.

O `start_odometer` continua vindo do corpo, **não** da leitura: quem decide o número é a pessoa
que confirmou na tela. A leitura é anexo, não fonte.

### `GET /usos/{id}/hodometro/{saida|chegada}`

Devolve os bytes da foto com o `content-type` gravado, **streaming pela API**. 404 se a viagem não
tem aquela foto.

**Não é URL pré-assinada**, e é decisão: presigned vaza uma URL que funciona por fora do
`require_module` e do vínculo de tenant durante todo o TTL — mandada num grupo de WhatsApp, abre
pra qualquer um. O volume aqui (uma foto por viagem, vista raramente) não paga esse risco. O
escopo segue o de `GET /usos`: quem tem `usages.read` vê de toda a Empresa, quem não tem vê só as
viagens do próprio condutor.

## Testes — na mesma entrega

- **`tests/unit/frota/`** (sem Docker) — a regra de `plausivel` nas bordas (igual ao prior, prior +
  2000, um a mais, e valor abaixo do prior), o cálculo de `delta`, e a montagem da chave de
  storage com o prefixo do tenant.
- **`tests/unit/core/`** — o `LocalDirectoryStorage` contra `tmp_path`: `put`/`get`/`delete`, e que
  `get` de chave inexistente levanta o erro do contrato, não `FileNotFoundError` cru.
- **`tests/integration/frota/`** — as rotas contra Postgres real, com o `StubOdometerReader` e o
  `LocalDirectoryStorage` injetados. **Nenhum teste fala com a rede**, e é a porta que garante.
  O `current_odometer` entra com `INSERT` direto, incluindo o caso da viagem aberta.

## Critérios de aceite

1. `src/modules/frota/` continua importando **só** `src.core` — nem `auth` nem `access` —, e
   `mount_routes` **não** ganha linha nova: `core/storage` é infra e se resolve pela config, como
   o `EmailSender` da `06`. Verificável por leitura de import e `git diff`.
2. `POST /veiculos/{id}/hodometro/leituras` com um JPEG responde **201** com `valor`, `confianca`,
   `plausivel`, `ultimo_hodometro` e `delta`, e grava uma linha em `odometer_readings` com
   `storage_key` preenchida — o objeto existe no storage sob a chave que começa com o
   `organization_id`.
3. Com o `StubOdometerReader` configurado pra se abster, a mesma rota responde **201** com
   `valor: null`, e **a linha e a foto são gravadas assim mesmo**. Não é 4xx: não conseguir ler é
   resultado, não erro.
4. Foto de **9 MB** responde 413; um `application/pdf` responde 415; um JPEG corrompido responde
   422. Nenhum dos três grava linha nem objeto.
5. Um `collaborator` com só `frota.usages.write_own` **consegue** ler (201); um `hr` (sem nenhuma
   capability de frota) recebe **403**. Numa Empresa sem o entitlement `frota`, **403** antes de
   qualquer validação.
6. A leitura de um veículo de **outra** Empresa responde **404**, e a de um veículo `inactive`
   responde **422**.
7. `GET /veiculos` e `GET /veiculos/{id}` devolvem `current_odometer`: igual a `initial_odometer`
   num veículo sem viagem; igual ao maior `end_odometer` depois de duas viagens encerradas; e
   igual ao `start_odometer` da viagem **aberta** quando esta é maior que todos os `end_odometer`.
   A listagem de 20 veículos resolve em **uma** query (sem N+1) — verificável por contagem de
   `SELECT`.
8. `plausivel` é `true` para `valor == ultimo_hodometro`, `true` para `ultimo_hodometro + 2000`,
   `false` para `+ 2001` e `false` para `ultimo_hodometro - 1`. Em **nenhum** desses casos a
   resposta deixa de ser 200/201 — `plausivel: false` **não** vira 422.
9. `POST /usos` com `leitura_saida_id` válido responde 201 e grava `start_reading_id`. Com uma
   leitura de **outro veículo**, **422**; com uma leitura **já apontada** por outra viagem, 422;
   com uma leitura de **outra Empresa**, 422. `POST /usos` **sem** leitura nenhuma segue
   respondendo 201 — a foto é opcional.
10. `GET /usos/{id}/hodometro/saida` devolve os bytes gravados com o `content-type` original;
    `.../chegada` numa viagem sem foto de chegada responde 404. Um `collaborator` recebe **404**
    ao pedir a foto de uma viagem de **outro** condutor — o mesmo escopo de `GET /usos`.
11. **Sobre fotos reais** (as de `.claude/spikes/hodometro-ocr/amostras/`, com o adaptador de
    produção e chave de verdade, fora da suíte automatizada): o motor lê corretamente o hodômetro
    em pelo menos **8 de 10** fotos em resolução usável, e nas que erra, **se abstém ou marca
    `confianca: "baixa"`** em vez de devolver número confiante e errado. Este critério existe
    porque o lado multimodal **não foi medido** antes desta spec — ver "A decisão do motor". Se
    falhar, o que muda é o adaptador; o resto da entrega fica de pé.
12. Uma leitura com mais de 24h e sem viagem apontando é apagada — linha **e** objeto — na próxima
    chamada de leitura da mesma organização; uma leitura de 23h, ou uma já apontada por viagem,
    **não** é tocada.
