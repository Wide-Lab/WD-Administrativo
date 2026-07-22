# 04 — Casca e personas — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Os cinco critérios batem. O **4** foi observado por `npm run test` (31 testes) e o contrato do
backend por `curl` contra o Postgres real, pela stack do compose; os de renderização (**1**,
**2**, **3**, **5**) foram verificados **no browser pelo Kauan**, não por mim — não há
testing-library no projeto, e eu não tinha browser disponível. Fica registrado quem observou o
quê. O que a implementação decidiu, e a spec não previa:

- **Os metadados de navegação vieram de um catálogo do frontend, não do contexto — a premissa
  da spec não era alcançável.** O texto diz que os itens "vêm dos descritores expostos no
  contexto (`modules` + metadados de nav do `ModuleDescriptor`)". Mas o
  `GET /api/organizacoes/{orgId}/me` devolve `modules` como **lista de chaves**
  (`["refeicoes"]`), e o `ModuleNav` (label/path/icon) só sai pelo
  `GET /api/organizacoes/{orgId}/modulos` — que a `backend/05` fechou para `platform_admin`.
  Um `collaborator` leva **403** lá, e é exatamente ele quem precisa do menu. Então o label e o
  path moram em `features/context/modules.ts`, chaveados pela chave do módulo.
  Mudar o payload do `/me` teria sido a outra saída, e foi recusada: ela quebra o contrato que o
  critério 3 da `backend/05` verificou, e o "sem deploy" **não se perde** — quem decide a
  visibilidade continua sendo o entitlement, e o catálogo só diz como o item se chama. As telas
  do módulo têm de existir no frontend de qualquer forma; um label vindo do servidor apontaria
  para uma rota que só um deploy cria. Se um dia o `/me` devolver os descritores (um módulo
  vendido a quem não fez deploy do frontend?), é spec própria — o `buildNav` já recebe o
  catálogo por parâmetro, então a troca é no chamador.
- **Não existem route groups por persona, e é decisão, não esquecimento.** A `00-visao-geral`
  previa `(admin)`/`(parceiro)`/`(colaborador)`; a estrutura desta spec já dizia outra coisa
  (`organizacoes/[orgId]/layout.tsx` "resolve a persona"), e ela venceu por um motivo estrutural:
  **route group é estático e persona é runtime** — ela vem do `/me`, depois do JS carregar. Um
  group por persona exigiria saber quem é a pessoa para escolher a URL, e a URL é o que dá o
  `orgId` que responde quem ela é. O seam por persona segue existindo, mas mora no `AppShell` e
  no `buildNav`, não na árvore de rotas. O `(publico)` foi criado, esse sim, e `/entrar` mudou de
  pasta sem mudar de URL.
- **A `/` virou roteador, não tela.** É o destino padrão do `safeNextPath` e o fallback de toda
  guarda, então ela lê o `/me/contexto` e manda pra home real — fechando o "destino guardado ou
  home da persona" que a `03` deixou em aberto. Quem decide é `homePathFor`, pura e testada:
  vínculo de plataforma ganha da lista; com vários vínculos cai no primeiro, porque **o seletor
  é a `05`**.
- **Sem vínculo nenhum é estado, com tela própria na `/`** — não estava na spec. É o convidado
  que ainda não aceitou (spec 06) ou quem teve o vínculo desativado: o backend omite do contexto
  o que não dá pra abrir, então `memberships: []` é uma resposta normal, e mandar essa pessoa pro
  login seria um laço.
- **403 no `/me` redireciona pra home real, em vez de "acesso negado".** A spec pede isso pra
  "group de persona sem vínculo compatível"; vale igual pro tenant alheio, porque o caso comum não
  é invasão — é URL velha ou link colado. Não há laço: a org que negou nunca está no
  `/me/contexto`.
- **`GET /api/organizacoes/{orgId}` entrou na `api.ts`, que a spec não listava.** A spec manda a
  home mostrar "o nome da org ativa", e **nenhuma das duas rotas do contexto o tem**: o `/me` não
  devolve nome, e o `/me/contexto` não lista a organização de um `platform_admin` sem vínculo nela
  — ele seria a única persona a ver um cabeçalho sem nome.
- **A casca tem duas formas, não quatro.** O Colaborador é mobile-first e vive na barra inferior;
  Plataforma, Administração e Parceiro ganham barra lateral no desktop e caem na mesma barra
  inferior no celular. Quatro cascas seriam quatro coisas pra manter onde o que muda é conteúdo e
  navegação — e essas já vêm resolvidas do `buildNav`.
- **`buildNav` filtra por persona _e_ por entitlement, e o segundo sozinho seria errado.**
  Verificado: o `/me` de um `platform_admin` na Acme devolve `modules: ["refeicoes"]` — módulos
  são do **tenant**, não da pessoa (a `backend/05` já dizia). Sem o filtro de persona, a
  Plataforma veria "Refeições" no menu, um módulo que não tem tela pra ela. Quem separa é
  `ModuleDescriptor.personas`, e é o que dá utilidade ao campo.
- **`ModuleGuard` não renderiza os filhos enquanto o contexto carrega**, e é isso que cumpre o
  "nunca dispara chamada que dependa dele": as chamadas do módulo saem de dentro dos filhos, então
  checar _depois_ de montar já teria batido no backend.
- **As páginas de `refeicoes`/`frota` são a única coisa aqui que as fases 2/3 apagam** em vez de
  estender. Existem porque sem uma rota de módulo o critério 3 não seria observável. O
  `ModuleGuard` que as embrulha, esse, é o que o módulo real herda.
- **`Can` só lista permissão que tem guard de verdade do outro lado.** A lista da home usa as
  capabilities de kernel reais (`access/domain/permissions.py`) — uma linha ali sem
  `require_permission` no backend seria cadeado pintado. Verificado no browser: `company_admin` vê
  conveniar + membros, `hr` vê só ver membros, `collaborator` não vê a lista (sem permissão de
  kernel, o card some inteiro).
- **`/plataforma` é casca sem lista de tenants.** A estrutura da spec diz "tenants, entitlements",
  mas listar tenants pra abrir um é **seleção de organização — a `05`** —, e a spec põe isso fora
  de escopo. Hoje a Plataforma alcança um tenant navegando pra `/organizacoes/{orgId}`. Ligar
  módulo segue sendo `PUT` ou CLI.
- **`isNavItemActive` foi junto pra `nav.ts`**, testada: a home casa exato e o módulo casa por
  prefixo. Compará-la por prefixo a deixaria acesa sempre (a home é prefixo de todo item), e sem
  o prefixo no módulo uma tela de dentro dele (fase 2) apagaria o menu.
- **Chave habilitada que o catálogo não conhece é ignorada em silêncio.** Backend e frontend sobem
  em containers separados: o backend pode ter um módulo que este deploy ainda não tem, e isso é o
  normal de um monólito em dois processos — não é erro que mereça quebrar o menu.
- **Sem testes de componente, e a dívida de teste do backend agora tem irmã no frontend.** As duas
  regras puras (`nav.ts`, `home-path.ts`) têm teste; a casca, os guards e o `Can` foram
  verificados só a olho, no browser, uma vez. São exatamente o tipo de coisa que quebra calada num
  refactor — e o `Can` guarda a mesma pergunta que um `require_permission` guarda no servidor.
  Uma spec de infra de teste de componente (testing-library + jsdom) é o candidato óbvio, e o
  argumento é o mesmo que a `backend/05` registrou.
