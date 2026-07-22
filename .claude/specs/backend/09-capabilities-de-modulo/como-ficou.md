# 09 — Capabilities de módulo — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Os nove critérios batem e foram observados rodando: 86 testes verdes em ~28s (69 + **17
novos**), `mypy src tests` e `ruff check .` limpos, e as duas falhas de subida verificadas
**no ponto de composição real** — `mount_routes` com um módulo de `grants` inválido estoura, e
a app não sobe. Nenhuma revisão de Alembic: o head segue `0005_invitations`, como a seção "Sem
migration" previa. O que a implementação decidiu e a spec não previa:

- **A soma acontece em _dois_ lugares, não num só — e a spec errou ao dizer "o único lugar".**
  O texto aponta `SqlAlchemyMembershipReader.get_permissions`, e ele de fato é o único ponto
  que o **guard** consulta. Mas o `GET /organizacoes/{orgId}/me` não passa pelo reader: o
  `GetMyMembershipUseCase` chama `permissions_for(role)` por conta própria, e sem tocá-lo o
  critério 4 não passaria — o `/me` responderia sem a capability de módulo enquanto a rota
  respondia 200. Então os dois somam o mesmo par. **É uma dívida, não um acerto:** são duas
  contas que precisam concordar e nada as obriga a isso, e o dia em que divergirem o menu vai
  prometer o que a rota recusa (ou escondê-la à toa). O conserto certo é o use case pedir a
  permissão pela mesma porta que o guard, e ele não coube aqui porque muda a forma do use case
  (passaria a receber o `PermissionReader`, não só a `uow`). Ficou um comentário nos dois
  pontos. **Quem mexer em `permissions` de novo unifica primeiro.**
- **O critério 8 cobra uma coisa que o payload nunca teve.** Ele pede que `GET .../modulos`
  devolva "o catálogo com a lista de capabilities vazia para os dois", mas o
  `CatalogModuleResponse` **não tem campo `permissions`** — a `05` decidiu isso de propósito
  ("o catálogo diz o que dá pra vender, e as capabilities de dentro do módulo são pergunta do
  `/me`"), e esta spec manda explicitamente não mudar o payload. As duas frases não cabem
  juntas, e a de não mexer no payload venceu: mudar o contrato de uma rota de `platform_admin`
  é decisão de produto, não efeito colateral de uma spec de mecanismo. O que ficou testado é a
  intenção do critério pelos dois lados que existem — a rota segue listando `refeicoes` e
  `frota` e o `PUT` segue ligando o flag, e a propriedade derivada `permissions` dos dois
  descritores é `frozenset()`.
- **A fixture de isolamento do registry mora no `conftest.py` raiz, e mexe em `_modules`
  direto.** Raiz, e não `integration/`, porque quem precisa dela é tanto o `unit/` (a validação
  é regra pura) quanto o `integration/` — e ela não toca banco, então não repete o erro que o
  docstring do `integration/conftest.py` registra. O acesso a `registry._modules` é a `_` que
  esta suíte tem: o registry não expõe "esqueça um módulo", e dar-lhe um `unregister` público
  seria inventar API de produção pra servir teste. Se um dia houver motivo real de produção pra
  desregistrar, a fixture passa a usá-lo.
- **A validação de namespace ganhou função própria (`_assert_grants_are_namespaced`) em vez de
  virar corpo do `register_module`.** É onde os três problemas que a regra resolve estão
  escritos — e eles são o tipo de coisa que alguém apaga por parecer paranoia. A mensagem do
  erro nomeia as capabilities ofensoras e aponta o helper `.permission()`, porque quem a lê
  está com a app fora do ar.
- **`module_permissions_for` devolve `frozenset()` sem módulo nenhum registrado, e isso exigiu
  cuidado.** `frozenset().union(*())` funciona, mas a escrita ingênua (`union(*(...))` sobre um
  gerador vazio, ou um `reduce` sem inicial) estoura — e o caso "nenhum módulo declara nada" é
  exatamente o estado do repo hoje, com `refeicoes` e `frota` em `grants={}`. Tem teste unitário
  só pra ele.
- **O módulo de prova `smoke` concede a `manager` de propósito.** É o único papel que sai de
  `PERMISSIONS_BY_ROLE` com `frozenset()` vazio junto de `finance`/`partner_operator`, então o
  200 do critério 1 **não pode** ter vindo do mapa do kernel. Escolher `company_admin` teria
  feito o teste passar por acidente.
- **A validação de papel roda no fim de `mount_routes`, e a de namespace em `register_module` —
  duas linhas do mesmo `RuntimeError`, em pontos diferentes.** A separação é a que a spec
  desenhou e ela se sustentou na prática: o `core` pegou `frota` concedendo
  `organizations.write` sem saber que papel existe, e o `access` pegou `"colaborador"` sem saber
  o que é namespace. Vale notar o que **nenhuma** das duas pega: um módulo que declara
  `grants` corretos pra um papel que não existe **naquele tipo de organização** (um
  `partner_admin` num módulo que só Empresa contrata). Isso não é erro — a concessão
  simplesmente nunca se realiza, porque não há vínculo daquele papel numa Empresa —, mas
  também não avisa ninguém. Se virar pegadinha recorrente na fase 2, é validação a mais.
- **`ModuleDescriptor` continua tecnicamente não-hasheável**, agora por causa do `Mapping` em
  vez do `Sequence`. Nada mudou na prática (a lista plana já o era), ele é sempre valor de dict
  e nunca chave, e `frozen=True` só gera `__hash__` — não o chama. Registrado porque o próximo
  a tentar `set[ModuleDescriptor]` vai descobrir isso do jeito difícil.
- **A seção "Sem migration" afirma que o `alembic check` continua limpo, e isso é falso**
  (anotado em 2026-07-20, depois que a `10` topou com o mesmo). A metade que se sustentou é a que
  importava aqui: esta spec realmente não gerou revisão nenhuma, e o head seguiu `0005`. A outra
  metade nunca foi verdade — `alembic check` já propunha dropar `fk_memberships_user` (0003),
  `fk_module_entitlements_granted_by` (0004) e `fk_invitations_invited_by` (0005) **antes** desta
  entrega, porque FK que cruza módulo vive só na migration e o `--autogenerate` não a enxerga no
  model. O erro foi de verificação, não de decisão: "não gerei migration" foi conferido, "o
  `check` está limpo" foi deduzido de lá sem rodar. A `10` acrescentou as três da frota e fez o
  registro completo — ver o `Como ficou` dela. Enquanto FK entre módulos viver só na migration,
  `alembic check` **nunca** será verde, e usá-lo em CI exige allowlist das seis; é decisão da spec
  de CI. **A lição pro próximo `Como ficou`:** afirmação sobre ferramenta só entra se a ferramenta
  foi rodada.
