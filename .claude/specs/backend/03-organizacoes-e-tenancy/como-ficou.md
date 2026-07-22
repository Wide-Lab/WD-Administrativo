# 03 — Organizações e tenancy — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Os critérios 1, 3, 4 e 5 batem e foram observados rodando contra o Postgres de verdade. O
**critério 2 ficou em aberto por dependência e fechou na spec 04**, e o 6 é vacuamente
verdadeiro hoje — detalhe abaixo.

> **Fechado na `backend/04` (2026-07-16).** O `SqlAlchemyOrganizationReader` agora confere
> `memberships` e afrouxa pra `platform_admin`, como este texto previa. Custou o que a spec
> dizia que custaria: o corpo de um método, mais uma consulta — nenhuma rota, use case ou linha
> do `core` mudou junto. Verificado rodando: um usuário vinculado só a um Parceiro leva **403**
> na Empresa alheia (e vice-versa), e o `platform_admin` alcança qualquer `orgId`. O parágrafo
> abaixo fica como o registro da decisão de subir permissivo — não some.

- **O critério 2 não fecha nesta spec, e isso é estrutural, não esquecimento.** O critério
  cobra 403 pra organização "em que o usuário não tem vínculo", mas vínculo é `memberships`,
  tabela da **spec 04** — que esta spec lista em `Fora de escopo`. Não havia como conferir
  vínculo sem construir a 04 junto. O texto já previa a saída ("esta spec pode subir com o
  guard ainda permissivo"), então: `current_organization` existe, é real e está ligado em
  **todas** as rotas escopadas; o que está permissivo é só o `SqlAlchemyOrganizationReader`,
  que hoje aceita qualquer organização **ativa** pra qualquer usuário **autenticado**.
  Verificado rodando: 401 sem sessão, e **403 de verdade** quando o reader nega — provado
  desativando uma organização (`status='disabled'` → 403 no detalhe e nos convênios). Apertar
  na 04 é trocar o corpo de um método; nenhuma rota, use case ou linha do `core` muda junto.
- **`OrganizationType` mora no `core`, não no `access`.** A spec diz "dependency
  `current_organization` (em `access`, exposta via `core`)", mas `CurrentOrganization` carrega
  o `type`, e um módulo de negócio precisa saber se está numa Empresa ou num Parceiro sem
  importar `access`. Duplicar o enum nos dois lados seria pior. Então o `core` é dono do
  **vocabulário** do contrato (`core/tenancy/`), e o `access` segue dono da **tabela** — a
  seta continua apontando pra dentro, porque quem importa `core` é o módulo.
- **`current_organization` chegou pelo mesmo padrão do `UserReader` da spec 02:** o `core`
  declara a porta `OrganizationReader`, o `access` registra a implementação em `mount_routes`
  (`set_organization_reader_factory`). O `access` é o **segundo** módulo com duas linhas no
  `mount_routes` — privilégio de kernel, como a spec 02 registrou.
- **O helper tenant-scoped virou duas peças, não uma.** A spec pedia "um helper de
  repositório"; o real tem `core/database/tenant.py` (`TenantScopedBase`, dono da coluna
  `organization_id`) além de `repositories/tenant_scoped.py`. Sem a base, o repositório
  genérico não teria como exigir, em tipo, que o model tem `organization_id` — e o escopo
  viraria disciplina em vez de estrutura.
- **Um bug real que só apareceu rodando:** `TenantScopedRepository.get_by_id_or_none` vazava
  linha de outro tenant. O repositório base resolve esse método com `session.get()` direto,
  **sem** passar pelo `_get_model_or_none` que eu havia escopado. Escopar só o helper não
  bastava; o método precisou de override próprio. É exatamente o furo que o critério 5
  existe pra pegar, e ele só apareceu porque o critério foi exercitado de verdade.
- **`POST /convenios` duplicado devolvia 500, não 409.** O `flush()` do repositório já manda o
  `INSERT`, então a constraint estoura **antes** do `commit` — e o `SQLAlchemyUnitOfWork` só
  traduz `IntegrityError` → `ConflictError` no `commit`. A tradução foi pro `create` do
  `PartnerAgreementRepository`. **O mesmo furo existe no `auth`** (e-mail duplicado no
  `UserRepository.create` também viraria 500); não foi corrigido aqui porque mudar o
  comportamento do `auth` é escopo da spec dele, mas fica registrado.
- **A organização `platform` é semeada na migration**, com id fixo
  (`01890000-0000-7000-8000-000000000001`). A spec exige "exatamente uma `platform`" mas
  nenhuma rota a cria (`POST /api/organizacoes` só faz Empresa e Parceiro, e o schema recusa
  `platform` com 422). Sem semear, o "exatamente uma" seria "no máximo uma, e zero na
  prática" — e o bootstrap do primeiro `platform_admin` (specs 02/04) não teria alvo. O "no
  máximo uma" quem garante é um índice único **parcial** (`WHERE type = 'platform'`).
- **Critério 6 é vacuamente verdadeiro**: não existe tabela de negócio ainda — `organizations`
  e `partner_agreements` são kernel, e o convênio é escopado por `company_id`/`partner_id`,
  não por `organization_id`. O que a spec entrega é a **impossibilidade** de esquecer:
  herdar de `TenantScopedBase` é o que dá acesso ao repositório tenant-scoped. O critério só
  passa a ter mordida quando o primeiro app de negócio chegar (fase 2).
- **Sem testes automatizados** — o backend não tem framework de teste, e esta spec não cita
  testes. A verificação foi por `curl` e `psql` contra o Postgres real, mais um script
  temporário pro critério 5, apagado depois. **É dívida**: o furo do `get_by_id_or_none` não
  tem hoje nenhuma rede que impeça a volta. Uma spec de infra de teste (`pytest` +
  Postgres efêmero) é o próximo candidato óbvio.
- **`PATCH /convenios/{id}` de convênio de outra Empresa responde 404, não 403** — quem não
  pode ver o convênio também não deveria descobrir que ele existe.
