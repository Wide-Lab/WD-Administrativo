# 10 — Frota (veículos, condutores e registro de uso) — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Os doze critérios batem e foram observados rodando: **216 testes verdes em ~70s** (86 + **130
novos**: 39 em `tests/unit/frota/`, 89 em `tests/integration/frota/`, mais os ajustes na suíte
existente), `mypy src tests` e `ruff check .` limpos. A migration `0006_frota` sobe do zero num
banco vazio, e a app monta as 14 rotas sob `/api/organizacoes/{orgId}/frota/*`. O que a
implementação decidiu e a spec não previa:

- **A promessa de "uma linha" custou três, e as outras duas são estruturais.** O critério 1 pede
  que `mount_routes` ganhe `mount_module(api, FROTA)` "e nada mais", e o `src/core` de fato não
  mudou **em nenhuma linha**. Mas o módulo precisou de mais dois pontos de contato fora de si:
  `migrations/env.py` importa os models da frota (sem isso as tabelas ficam fora do
  `target_metadata` e o `--autogenerate` propõe dropá-las — o próprio arquivo já dizia "importe
  aqui os models de cada módulo"), e `src/api/modules.py` perdeu o placeholder `FROTA`, que virou
  `src/modules/frota/module.py`. Nenhuma das duas é um `set_*_factory`, então o **privilégio de
  kernel** segue intacto; mas "uma linha" era otimista, e o próximo app de negócio vai pagar as
  mesmas três.
- **`PageResponse`, `get_page_params` e o helper `_pg_enum` foram duplicados, e não havia saída
  boa.** Os três moram no `access` (`adapters/http/schemas.py`, `adapters/http/dependencies.py`,
  `adapters/db/models.py`), um app de negócio não importa `access`, e promovê-los ao `core` é
  exatamente o que o critério 1 proíbe. Então a frota tem os seus, com o porquê no docstring.
  **É a primeira dívida de verdade que o seam de extração cobra**, e ela cresce a cada módulo
  novo: Refeições vai duplicar os mesmos três. O conserto certo é uma spec própria promovendo
  essas conveniências de HTTP pro `core` — decisão de arquitetura, não efeito colateral desta
  entrega.
- **O `GET /usos` precisou de um `PermissionReaderDep` que a superfície pública do `core` não
  exporta.** `src/core/authz/__init__.py` exporta `require_permission` (que **levanta**) mas não
  o reader (que só **lê**), e a rota de escopo-por-capability precisa exatamente do segundo: ela
  não nega, ela decide o que devolver. A frota importa de `src.core.authz.context` — ainda `core`,
  ainda sem mudar `core`, mas furando a fachada. É candidato natural ao mesmo conserto do item
  anterior.
- **`driver_id` virou opcional no `POST /usos`, e sem isso o critério 4 não fecharia na
  prática.** A spec exige 403 quando quem tem só `write_own` aponta outro condutor — o que
  pressupõe que ele saiba o próprio `driver_id`. Mas o `collaborator` **não tem
  `frota.drivers.read`** (decisão da própria spec), então não há rota pela qual ele o descubra:
  exigir o campo tornaria impossível o único gesto que a spec lhe dá. Omitir passou a significar
  "eu", resolvido pelo condutor vinculado ao `user_id`. Mandar o próprio explicitamente continua
  valendo, e mandar o de outro continua sendo 403.
- **`ex_vehicle_usages_no_overlap` usa `tstzrange` `[)`, e isso decide o uso normal da frota.** A
  spec não diz qual borda; o default do Postgres é fechado-aberto, e é o certo: a viagem que
  termina às 12h e a que começa às 12h **não** colidem. Com `[]`, devolver o carro e outro pegá-lo
  no mesmo minuto seria 409 — o caso mais comum do dia vira erro. Tem teste só pra essa borda.
- **A constraint de exclusão está no model (`ExcludeConstraint`) e em SQL cru na migration.** No
  model porque é onde as outras invariantes de `vehicle_usages` estão escritas e alguém vai
  procurá-la ali; em SQL cru na migration porque `op.create_exclude_constraint` não alcança a
  expressão `tstzrange(...)`. O DDL que o model compila é idêntico ao da migration — conferido.
- **Os models herdam `TenantScopedBase` mas sobrescrevem o `organization_id` pra tirar a FK
  simples dele.** Herdar é o que os torna elegíveis ao `TenantScopedRepository` (o escopo de
  tenant vira estrutural); a FK simples pra `organizations.id` que a base traz é substituída pela
  **composta** contra `organizations(id, type)`, que é estritamente mais forte — garante que a
  organização é uma `company`. Manter as duas seria redundante e faria a simples aparecer como
  diferença em todo `--autogenerate`. Ficou um `CompanyScopedBase` local com o porquê.
- **`_constraint_of` precisa percorrer `__cause__`, e descobrir isso custou uma rodada
  vermelha.** O `exc.orig` de um `IntegrityError` do asyncpg é o erro **já traduzido pelo
  dialeto**, que não carrega `constraint_name`; quem o carrega é a exceção original do asyncpg, um
  nível abaixo. Olhando só o topo, toda violação virava 500 em vez do 409/422 que ela merece — e o
  teste de placa duplicada foi quem pegou. Vale pro próximo módulo que traduzir `IntegrityError`.
- **O `alembic check` não está limpo — e já não estava antes desta spec.** Ele reporta seis
  `remove_fk`, e **três são pré-existentes**: `fk_memberships_user` (0003),
  `fk_module_entitlements_granted_by` (0004) e `fk_invitations_invited_by` (0005), todas com o
  comentário "um `--autogenerate` futuro vai propor dropá-la. Recuse." nas próprias migrations. A
  frota acrescenta as suas três (`fk_vehicles_organization`, `fk_drivers_organization`,
  `fk_vehicle_usages_organization`), do mesmo tipo e pelo mesmo motivo. **Isto contradiz a seção
  "Sem migration" da `09`, que afirma "o `alembic check` continua limpo"** — a afirmação era falsa
  quando foi escrita, e este é o registro. (A `09` foi anotada em 2026-07-20 e agora aponta pra
  cá.) Enquanto FK entre módulos viver só na migration, `alembic
  check` **nunca** será verde, e usá-lo em CI exige uma allowlist dessas seis. Vira decisão da
  spec de CI.
- **Dois testes existentes quebraram, e as duas quebras eram staleness legítima.**
  `test_o_banco_esta_na_ultima_migration` fixava `0005_invitations` (agora `0006_frota`), e
  `test_module_permissions_for_soma_os_descritores` afirmava igualdade exata sobre
  `module_permissions_for(MANAGER)` — que passava **só porque todo módulo real declarava
  `grants={}`**. Era verde por acidente do repo estar vazio, não por isolamento: `registry_isolado`
  salva e restaura, mas não limpa. Nasceu daí a fixture `registry_vazio`. O terceiro ajuste foi o
  critério 8 da `09` (`FROTA.permissions == frozenset()`), que a `10` tornou falso por construção
  — está anotado no próprio teste em vez de apagado.
- **O `manager` é o papel de prova de toda a suíte de integração, e é escolha.** Ele sai de
  `PERMISSIONS_BY_ROLE` com `frozenset()` vazio, então **todo 2xx que ele tira nas rotas de frota
  só pode ter vindo do `grants` do descritor**. Um `company_admin` faria metade dos testes passar
  por acidente, porque ele já tem capabilities de kernel. Mesma receita do módulo `smoke` da `09`.
- **O critério 1 virou teste, não inspeção.** "A frota não importa `auth` nem `access`" é
  verificável por leitura de import, e ficou um teste que varre `src/modules/frota/**.py` — um
  `from src.modules.access...` acrescentado daqui a seis meses quebra a suíte em vez de passar
  despercebido num code review. Junto vai o contrapositivo (a frota **importa** `src.core`), senão
  o teste passaria num diretório vazio.
- **`GET /usos` é a única rota do módulo sem `require_permission`, e isso é o desenho.** Ela exige
  só o entitlement; a capability decide o **escopo** do que volta. O filtro `?condutor=` de quem
  não tem `usages.read` é **sobrescrito**, não somado — pedir o condutor de outro não pode virar
  um jeito de vê-lo, e tem teste pra isso.
- **Não há `DELETE` de veículo nem de condutor, e o 405 é do FastAPI**, não de um handler que
  responde 405. O critério 10 aceita "405/404"; ficou 405 porque a rota existe pro `PATCH` e o
  método é que não. Nada a implementar — mas está testado, porque "não existe" é uma afirmação
  que alguém pode desfazer sem notar.
- **`initial_odometer` continua sem uso funcional.** Ele é gravado e devolvido, mas nada o lê: o
  hodômetro atual é derivado do maior `end_odometer`, e o relatório soma diferenças por viagem.
  Ele existe porque a spec o pede e porque o primeiro relatório de "km total do veículo desde o
  cadastro" vai precisar dele — mas hoje é dado morto, e é honesto dizê-lo.
- **A validação de `ended_at` no futuro ficou de fora.** A spec só menciona `started_at`, e foi o
  que se implementou. Uma viagem que começou ontem e "termina" semana que vem passa. Não parece
  intencional na spec, mas inventar a regra aqui seria expandir escopo; fica registrado como
  candidato a ajuste de uma linha.
