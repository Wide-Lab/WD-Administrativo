# 04 — Membros e autorização — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Os cinco critérios batem e foram observados rodando contra o Postgres real, pela stack do
compose (nginx → backend), incluindo os 401 e 403. O que a implementação decidiu e a spec não
previa:

- **`require_permission` mora num pacote novo, `core/authz/`, e chegou pelo mesmo padrão das
  specs 02/03:** o `core` declara a porta `PermissionReader`, o `access` registra a
  implementação em `mount_routes` (`set_permission_reader_factory`). Com isso o `access` passa
  a ter **três** linhas no `mount_routes`, não duas. É teto e não escada: são os três eixos que
  o kernel expõe (identidade fica no `auth`), e o `require_module` da spec 05 reusa o mesmo
  pacote. App de negócio segue com sua linha única — provado rodando, ver o critério 5 abaixo.
- **`Permission` é `str`, não enum, e o `core` não tem catálogo.** A spec diz que o kernel
  declara as permissões da plataforma e cada módulo de negócio declara as suas (spec 05). Se o
  `core` fosse dono do enum, todo módulo novo o obrigaria a mudar — a seta voltaria a apontar
  pra fora. O catálogo do kernel é `access/domain/permissions.py`. O custo é que um typo em
  `require_permission("agrements.write")` só aparece como 403 em runtime; a spec 05 pode fechar
  isso quando houver mais de um declarante.
- **Os nomes das permissões divergem do exemplo da spec.** O texto cita `company.manage_members`;
  ficou `members.read`/`members.write`. Duas razões: a mesma permissão serve organização
  `partner` (um `partner_admin` lista os membros do Parceiro), e o prefixo `company.` mentiria
  ali; e o esquema `<recurso>.<ação>` é o que o `agreements.write` da própria spec já usava.
  Os nomes eram "ex.:", ilustrativos — a forma do contrato (guard por capability, não por
  papel) está preservada.
- **`platform_admin` **não** recebe `agreements.write`, de propósito.** Conveniar é ato da
  Empresa e o convênio carrega os termos _dela_; a plataforma provisiona tenants e conserta
  vínculos, não assina contrato no lugar do cliente. Bate com a tabela da spec 03, que dá
  `/convenios` a `company_admin`. Verificado: `platform_admin` → `POST /convenios` responde 403.
- **`finance`, `manager` e `partner_operator` saem sem permissão nenhuma de kernel**, e isso é
  esperado, não esquecimento: o que esses papéis fazem (aprovar fatura, ler catálogo) são
  capabilities de módulo de negócio, que a spec 05 deixa cada módulo declarar. Eles existem
  aqui porque o papel é o que o convite (spec 06) atribui, e porque já mudam a persona.
- **`GET /api/organizacoes/{orgId}/me` não devolve `modules`.** O payload de exemplo da spec o
  mostra, mas o texto logo abaixo diz que "`modules` entra no payload por org na spec 05".
  Devolver `[]` agora afirmaria que o tenant não tem módulo nenhum, quando a verdade é que
  entitlement não existe — e o frontend não teria como distinguir as duas coisas.
- **O critério 2 virou estrutura no banco, não um `if`.** `memberships` carrega um
  `organization_type` denormalizado, ancorado por FK composta contra `organizations(id, type)`
  (o mesmo truque do convênio, spec 03), e um `CHECK` de papel×tipo se apoia nele. Sem a FK
  composta o CHECK seria decorativo — bastaria gravar o tipo errado. O `CHECK` é **gerado** de
  `ROLES_BY_ORGANIZATION_TYPE`, pra banco e domínio não divergirem. Verificado por `psql`, por
  fora da aplicação: `hr` num `partner` viola o CHECK; mentir no `organization_type` viola a
  FK; e mudar o `type` de uma organização com vínculo é bloqueado. A aplicação explica (422
  legível), o banco impede.
- **A FK `memberships.user_id → users.id` existe só na migration, não no model — e foi um
  achado de execução.** Declarada no model, ela exigiria que a tabela `users` estivesse no mesmo
  `Base.metadata` na hora em que o mapper resolve, ou seja, que `access` importasse os models do
  `auth`: módulo importando módulo, o que sustenta o seam de extração. O furo apareceu rodando —
  a CLI do `access` quebrou com `NoReferencedTableError`, porque é um entrypoint que não tem
  motivo pra conhecer `auth`. Integridade referencial é do banco; o model só precisa da coluna.
  **Dívida registrada:** como o model não a declara, um `alembic revision --autogenerate` futuro
  vai propor dropar `fk_memberships_user` — há um comentário na migration mandando recusar.
- **A spec não previa CLI, e sem ela a 04 trancaria a porta com a chave dentro.** Nenhuma rota
  cria vínculo (criar membro é convite, spec 06) e nenhuma rota de plataforma responde sem um
  `platform_admin` existir. A spec 02 já tinha deixado isso pra cá ("O vínculo com a organização
  plataforma é dado pela spec 03/04"), então: `python -m src.modules.access.cli grant --email …
--role … [--org …]`; sem `--org`, o alvo é a organização `platform`, que é única. Ela resolve o
  e-mail por SQL cru em `users` — a regra que vale é a de _import_ entre módulos, e nenhuma
  classe do `auth` atravessa a fronteira.
- **`/me` de um `platform_admin` numa Empresa onde ele não tem vínculo** devolve papel
  `platform_admin` e persona `platform`, em vez de inventar um vínculo local. Ele alcança
  qualquer tenant (a checagem afrouxada que a spec 03 pediu) sem ter linha em `memberships`
  daquela Empresa; o `PermissionReader` **soma** as duas fontes, e é isso que faz a linha
  `PATCH /membros/{id}` da spec (`company_admin` **ou** `platform_admin`) valer sem um `if` na
  rota. Verificado: a plataforma desativou um membro da Acme sem ter vínculo lá.
- **Um vínculo só conta se ele e a organização estiverem ativos.** Não estava na spec e é
  decisão de produto: desativar uma organização derruba todo mundo nela sem tocar vínculo por
  vínculo, e desativar um vínculo derruba a pessoa sem apagar histórico. Verificado: com o
  vínculo `disabled`, a Ana levou 403 na Empresa e a Empresa sumiu do `/me/contexto` — o
  contexto lista o que a pessoa _pode abrir agora_, senão o seletor de organização ofereceria
  uma porta trancada.
- **`require_platform_admin` é o único guard que não passa por `require_permission`**, e a razão
  é estrutural: `require_permission` resolve a permissão dentro da organização do path, e
  `POST`/`GET /api/organizacoes` não têm `orgId` — provisionar tenant é o ato que antecede o
  tenant. Lá a pergunta não é "nesta organização", é "na Widelab".
- **`CompanyAdminDep` virou `AgreementWriterDep`**: o guard passou a nomear a capability, não o
  papel. Continua sendo `company_admin` na prática (só ele tem `agreements.write`), mas mudar
  isso agora é editar um `frozenset`, não caçar rotas.
- **O critério 5 foi verificado com um módulo de negócio descartável de verdade**, não por
  leitura: um `modules/smoke/` que importava **só** `src.core.authz` e `src.core.tenancy`,
  ligado por uma linha no `mount_routes`. Rodando: 200 pra `company_admin`, 403 pra `hr`, 403
  pra quem não tem vínculo no tenant, 401 sem sessão. Apagado depois, e o 404 confirmado.
- **Sem testes automatizados** — o backend segue sem framework de teste e esta spec não cita
  testes; a verificação foi por `curl` e `psql`. **A dívida que a spec 03 registrou continua de
  pé e cresceu**: o mapa papel→permissões e o CHECK gerado são exatamente o tipo de coisa que um
  teste barato protegeria. Uma spec de infra de teste (`pytest` + Postgres efêmero) segue sendo
  o próximo candidato óbvio.
- **`PATCH /membros/{id}` de vínculo de outra organização responde 404, não 403** — mesma
  escolha do `PATCH /convenios/{id}` (spec 03): quem não pode ver também não deveria descobrir
  que existe. E o corpo vazio (`{}`) responde 422: `None` ali é "não mexe", não "apaga".

## Depois — 2026-07-23: as duas dívidas que a `frontend/08` cobrou

A tela de membros existiu, foi usada, e devolveu duas contas pra cá. Nenhuma das duas era achado
novo: as duas estavam escritas como dívida no `Como ficou` da `frontend/08` — a primeira como "o
terceiro achado de backend, e é o que mais dói", a segunda como um comentário em
`member-row-form.tsx` pedindo pra **não** consertar o buraco na tela. Foram fechadas juntas
porque são o mesmo `PATCH` e a mesma linha da tabela.

### `MemberResponse` ganhou `name` e `email` — por uma porta, não por um join

A lista de membros exibia UUID porque a resposta só tinha `user_id`, e `access` não pode importar
`auth` pra ler `users`. As saídas eram três: uma rota de diretório no kernel (`GET /usuarios/{id}`,
que resolveria isto e abriria uma superfície nova de leitura de identidade), um join impossível, ou
**um verbo a mais na porta que já existe**. Ficou a terceira: `UserReader`, em
`core/security/identity.py`, ganhou `list_profiles_by_ids` e um `UserProfile`; o `auth` a
implementa no `SqlAlchemyUserReader`, e o `ListMembersUseCase` cruza a página.

O que isso preserva é o que importa: **o `mount_routes` não ganhou linha**. A porta já era
registrada, e a regra da casa ("ganhar linha no `mount_routes` é privilégio de kernel") continua
valendo com as mesmas cinco. `UserProfile` é tipo separado de `CurrentUser` de propósito, embora
os campos sejam os mesmos — um é o sujeito autorizado da requisição, o outro é um terceiro numa
lista, e fundi-los faria um `if user.id == …` escrito por engano virar bug de autorização.

Duas decisões pequenas que valem registro:

- **em lote, e não um `get` por linha.** A versão singular convidaria ao N+1 sem que nada no tipo
  denunciasse. São duas consultas por página, e é o preço do seam;
- **sem filtro por `status`**, diferente do `get_active_by_id` logo ao lado. São perguntas
  opostas: aquele decide quem entra, este diz quem é o dono de um vínculo que existe. Esconder o
  nome de quem foi desativado deixaria a linha anônima justamente na tela que serve pra reativá-la.

O `PATCH` devolve o mesmo formato — senão a tela teria duas formas do mesmo objeto pra parsear, e
o membro recém-editado voltaria a ser um UUID até alguém recarregar.

### Ninguém edita o próprio vínculo: 422

Um `company_admin` se rebaixava a `collaborator` e a organização ficava sem quem a administre, sem
erro nenhum. A trava é por tabela — **papel e status, sempre** —, e não uma regra que compara
papéis: `members.write` só existe em `company_admin`, `partner_admin` e `platform_admin`, então
toda mudança que alguém faria na própria linha é rebaixamento ou desativação.

**O efeito colateral é que a regra do "último administrador ativo" não precisou existir.** Ela
estava na lista de dívidas junto com esta, e cai por consequência: se ninguém tira a si mesmo, e
cada um só edita os outros, sempre sobra pelo menos quem editou. Uma consulta a menos, e uma
regra a menos pra alguém manter.

422 e não 403 porque a permissão está lá — quem pede *tem* `members.write`; o que não existe é o
ato. E a checagem vem **depois** do 404 de vínculo de outra organização, pra não trocar a ordem de
quem descobre o quê.

A rota passou a receber `CurrentUserDep`: ela já sabia o que era preciso poder fazer, e o que
faltava era saber *quem* pedia.

### Testes

`tests/integration/access/test_membros.py`, 8 casos: a listagem com nome e e-mail, a listagem
mostrando quem foi desativado nas duas pontas (vínculo e identidade), o `PATCH` devolvendo
identidade junto, o auto-rebaixamento e a auto-desativação recusados — com conferência no SQL de
que o papel **não** mudou —, a trava valendo pro `partner_admin` e pro `platform_admin`, e o par
que impede tudo isso de virar "ninguém edita ninguém": o admin segue editando os outros. A suíte
de `access` foi a 71.
