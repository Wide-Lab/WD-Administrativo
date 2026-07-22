# 11 — Leitura de hodômetro por foto — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Onze dos doze critérios batem e foram observados rodando: **317 testes verdes em ~84s** (216 +
101 novos), `mypy src tests` e `ruff check .` limpos, e a migration `0007_odometer_readings` sobe
do zero num banco vazio. O **critério 11 não foi verificado**, e o porquê está na primeira seção
abaixo, porque é o item mais importante desta entrega.

### O critério 11 não pôde ser verificado, e isso não é detalhe

A spec fecha com: *"Sobre fotos reais (as de `.claude/spikes/hodometro-ocr/amostras/`, com o
adaptador de produção e chave de verdade): o motor lê corretamente o hodômetro em pelo menos 8 de
10 fotos"*. Nenhuma das duas condições existe no repo:

- **`.claude/spikes/` não existe.** O diretório inteiro do bake-off — as fotos, os scripts e os
  números do Tesseract — nunca foi commitado. A spec o cita como se fosse artefato versionado, e
  ele é memória de sessão. As três colunas da tabela "acerto exato / errado com confiança / valor
  correto nunca produzido" **não são reproduzíveis a partir deste repo**.
- **Não há `OPENAI_API_KEY` configurada**, nem no `.env` nem no ambiente.

Então o `OpenAIOdometerReader` **nunca falou com a OpenAI**. Ele está escrito, tipado e coberto
por lint — e é código não exercitado, que é a categoria de código que mais mente sobre estar
pronto. O que a spec já dizia continua valendo e agora com mais força: *"esta spec não promete
taxa de acerto"*, e *"se o motor não entregar, o que muda é o adaptador, não o desenho"*. O
desenho está de pé e testado inteiro contra o `StubOdometerReader`; o motor é a peça que falta
provar, e ela é uma classe de 130 linhas atrás de uma porta.

**Quem for fechar o critério 11 precisa de duas coisas que esta entrega não produziu:** as fotos
(recolher de novo, e desta vez commitar em `.claude/specs/backend/11-leitura-de-hodometro/`, que
é onde anexo de spec mora) e uma chave. Até lá, a funcionalidade em dev **se abstém sempre** — e
é honesta ao fazê-lo.

### O que a implementação decidiu e a spec não previa

- **A allowlist do `alembic check` vai mesmo pra sete, mas quase foi oito — e o erro foi meu.** A
  spec prevê que só `fk_odometer_readings_organization` entre na lista, porque as FKs internas ao
  `frota` vivem no model. Na primeira versão eu declarei `fk_odometer_readings_vehicle` **só na
  migration**, e o `alembic check` passou a propor dropar **oito**. Foi pego rodando o comando de
  verdade contra um Postgres descartável, não por leitura — e é o argumento a favor de conferir a
  afirmação em vez de repeti-la. Com a FK no model, o `check` reporta exatamente as sete previstas.
  **A memória de sessão que dizia "seis" está desatualizada a partir desta spec.**

- **O dataclass da porta virou `OdometerReadingResult`.** A spec o chama `OdometerReading`, que é
  o nome da **entidade persistida** — e as duas convivem em quase todo arquivo desta entrega. A
  forma (os quatro campos e o que cada um significa) é a do contrato; só o nome local mudou, que
  é o que o processo permite adaptar.

- **A extensão da chave de storage segue o `content-type`, e não é sempre `.jpg`.** A spec escreve
  `{organization_id}/frota/hodometro/{uuid7}.jpg`, mas PNG e WebP também são aceitos, e um PNG
  guardado sob `.jpg` confundiria justamente quem abre o bucket — que é o uso operacional que a
  chave existe pra servir. O prefixo do tenant, que é o que o critério cobra, não mudou.

- **O `content-type` mora no storage, não na tabela.** `odometer_readings` não tem coluna pra ele,
  e o `ObjectStorage.get` promete devolvê-lo — então cada adaptador o guarda do seu jeito: metadado
  do objeto no S3, um arquivo `.content-type` ao lado no diretório local. Inferi-lo da extensão
  seria adivinhar, e o `GET .../hodometro/{saida|chegada}` precisa do valor gravado.

- **A ordem da purga de órfãs foi invertida em relação ao texto.** A spec diz "antes de gravar a
  nova, apaga… linha e objeto". As **linhas** saem antes, na mesma transação da leitura nova; os
  **objetos** só somem depois do commit. Se a transação voltasse atrás com os arquivos já
  apagados, leituras válidas ficariam apontando pro nada — que é pior que o lixo que a purga
  recolhe. Falha ao apagar arquivo não derruba a requisição: vai pro log.

- **`UsageResponse` ganhou `start_reading_id` e `end_reading_id`, que a spec não lista.** A
  `frontend/10` precisa deles: o ícone de foto na lista de viagens só aparece quando há foto, e
  derivá-lo de uma chamada por linha seria N+1 na tela. São ids, não URLs — os bytes seguem
  saindo só pela rota com guard.

- **Os nomes de campo ficaram misturados no mesmo corpo, e é feio.** `POST /usos` agora recebe
  `vehicle_id`, `started_at`, `start_odometer`… e `leitura_saida_id`. A spec fixou os dois em
  português e a `frontend/10` já codifica contra eles; traduzi-los aqui deixaria o contrato
  divergente das duas specs de uma vez. O mesmo vale pra resposta da leitura, que é inteira em
  português (`valor`, `confianca`, `plausivel`, `ultimo_hodometro`, `delta`). **Fica registrado
  como inconsistência assumida**, não como padrão: o resto do módulo segue em inglês, e quem
  escrever a `refeicoes` não deve tomar isto como exemplo.

- **`"media"` sem acento.** A spec só mostra `"alta"` e `"baixa"`; o valor do meio ficou `media`,
  como todo valor de enum que o frontend compara por igualdade neste projeto.

- **"Uma leitura não pode estar em duas viagens" é checagem de aplicação, sem apoio do banco.** A
  regra é cruzada — a mesma foto não pode ser saída de A **nem** chegada de B —, e dois índices
  únicos parciais (um por coluna) não a expressariam: dariam meia garantia e ainda exigiriam o
  `SELECT`. Ficou um mecanismo só. **O custo é uma corrida estreita**: duas requisições
  simultâneas apontando a mesma foto passam as duas. É a única invariante desta spec que não mora
  no banco, e está aqui pra não virar folclore.

- **`VehicleRepository` relê o veículo depois de `POST` e `PATCH`.** O `create`/`update` do `core`
  monta a entidade a partir do model, e ali o `current_odometer` seria um palpite — o
  `initial_odometer` de um carro que pode ter dez viagens. Custa um `SELECT` a mais em escrita de
  veículo, que é rara; devolver um número errado, não. Tem teste.

- **`paginate` de veículo não reusa o `_paginate` do `core`.** Aquele faz `result.scalars()`, que
  descarta toda coluna depois da primeira — e é na segunda que o `current_odometer` do `LEFT JOIN`
  vem. É a segunda vez que a fronteira com o `core` cobra duplicação neste módulo (a primeira foi
  `PageResponse`/`get_page_params` na `10`), e reforça o caso da spec que promove essas
  conveniências.

- **O teste de N+1 mede constância, não um número.** O critério pede "uma query pra 20 veículos";
  o que ficou testado é que a contagem de `SELECT` **não muda** entre 2 e 20 veículos, mais uma
  asserção de que a listagem faz exatamente dois `SELECT` em `vehicles` (o `count` da paginação é
  herdado do `core` e vale pra todas as listagens do projeto). Um `current_odometer` derivado por
  consulta-por-veículo passaria em todos os outros testes e só apareceria em produção.

- **O stub que se abstém é também o default de dev, e isso vai além da spec.** A spec descreve o
  `StubOdometerReader` como "testes, devolve valor fixo". Sem `OPENAI_API_KEY`, é ele que responde
  em dev — configurado pra **se abster**, nunca pra inventar um número. É o gêmeo do
  `LoggingEmailSender`: o fluxo funciona fim a fim sem provedor, e o que sai é honesto. Um stub
  que devolvesse `45210` faria a tela parecer pronta e o primeiro teste em campo descobrir que
  nunca esteve.

- **Três exceções novas no `core`** (`PayloadTooLargeError`, `UnsupportedMediaTypeError`,
  `TooManyRequestsError`), porque 413, 415 e 429 não existiam no vocabulário do projeto. O
  critério 1 proíbe **linha nova em `mount_routes`** e exige que o `frota` importe só `src.core` —
  as duas coisas valem —, mas ele **não** repete o "zero mudança em `src/core`" da `10`: a própria
  spec põe `core/storage/` no núcleo. O que mudou no `core` foi `config.py`, `exceptions.py` e a
  pasta nova; `mount_routes` e `api/modules.py` não mudaram em nenhuma linha.

- **Três dependências novas:** `pillow` (validar imagem, exigido pela spec), `openai` (o motor) e
  `aioboto3` (o `S3ObjectStorage`). A terceira é a mais pesada e a única que **nenhum teste
  exercita** — o `S3ObjectStorage` está escrito porque a spec o decide e porque
  `STORAGE_BACKEND=s3` seria mentira sem ele, mas ele está na mesma categoria do adaptador da
  OpenAI: código não exercitado.

- **O `docker-compose.yml` ganhou o `minio`, na rede interna.** O `nginx` não o expõe, como a spec
  manda: o bucket não é público, e todo byte sai pela API. Ele **não** foi subido nem testado
  nesta entrega.

- **Um teste teve o payload de 9 MB movido pra dentro do corpo.** Passá-lo no `parametrize` fez o
  pytest embutir os 9 MB no **id do teste** e imprimi-los em qualquer relatório — 72 MB de saída
  numa rodada com erro. Vale pra quem for testar upload de novo.

## O que ficou de dívida

1. **O critério 11**, acima — o único aberto, e o que decide se a funcionalidade é confiável.
2. **`OpenAIOdometerReader` e `S3ObjectStorage` sem nenhuma execução real.** Os dois estão atrás
   de portas, o que limita o estrago, mas nenhum dos dois rodou uma vez.
3. **A corrida na checagem de "leitura já apontada"**, descrita acima.
4. **A memória de sessão sobre o `alembic check` diz seis; são sete a partir daqui.**
