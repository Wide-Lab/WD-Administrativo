# 08 — Gestão de convites (listar, revogar, Parceiro convida) — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Os nove critérios batem e foram observados rodando: **19 testes novos** em
`tests/integration/access/test_invitations.py` (33 no arquivo, 235 na suíte), contra o Postgres
de verdade do harness da `07`, incluindo os 401, 403, 404, 409 e 410. `ruff`, `ruff format
--check` e `mypy src tests` limpos. O que a implementação decidiu e a spec não previa:

- **O `status` efetivo virou uma regra escrita duas vezes, e essa é a dívida desta spec.** Ele
  já existia em Python (`Invitation.effective_status`), e o filtro `?status=` precisou de um
  gêmeo em SQL (`_effective_status_condition`, no repositório). Não dava pra reusar o primeiro:
  o `total` da paginação sai de um `COUNT` sobre a mesma query, e filtrar em Python **depois** de
  paginar faria a lista contar vencidos como pendentes e devolver menos itens do que o número que
  ela própria anuncia — paginação que mente é pior que paginação que falta. As duas podem
  divergir em silêncio, então o que as segura junto é um teste, não um comentário:
  `test_o_filtro_de_status_responde_pelo_efetivo_e_o_default_e_pending` compara, convite a
  convite, o status que o **SQL** selecionou com o que a **entidade** derivou. Filtrar por `X` e
  receber um item que diz `Y` acusa a divergência na hora.
- **`InvitationResponse.from_entity` passou a exigir `now`, e o `POST` mudou junto.** A spec só
  cobrava o efetivo na listagem, mas deixar o `now` opcional daria duas verdades pro mesmo campo
  — e a errada seria a mais curta de escrever. No `POST` a diferença é nula (convite recém-criado
  nunca está vencido), então o custo foi um argumento e o ganho é não haver caminho pra um
  `status` cru vazar pra resposta.
- **A ordem é escrever primeiro, ler depois — e a leitura não decide nada.** A spec pedia o
  `UPDATE` condicional; o que ela não dizia é onde encaixar a leitura que separa 404 de 409 de
  204. Ler antes reintroduziria exatamente a janela que o `UPDATE` condicional existe pra fechar.
  Ficou: `mark_revoked_if_pending` decide (no banco, com `organization_id` **dentro** do mesmo
  `WHERE`), e só se ele devolver `False` é que uma leitura roda — pra *explicar* o que já
  aconteceu. A leitura não tem poder de escrita nenhum.
- **Isso exigiu um teste de forma, não de resultado, e ele é o mais valioso da entrega.**
  Trocar a implementação por `if convite.status is PENDING: update(...)` passaria em todos os
  outros testes desta spec e reintroduziria a corrida. Em
  `test_a_revogacao_e_guardada_pelo_banco_e_nao_por_uma_leitura` a leitura **mente**: um
  `monkeypatch` faz `get_by_id_or_none` jurar que o convite está `pending` enquanto o banco o tem
  como `accepted`. Numa implementação que decide pela leitura, a mentira vira escrita e o
  `accepted` é sobrescrito; na real, a coluna continua `accepted`. A asserção é sobre o **banco**,
  não sobre o status HTTP — sob uma leitura mentirosa o código de resposta é artefato do teste.
- **Revogar um convite vencido é 204 e grava `revoked`.** A spec tabela os estados por *coluna*,
  e um vencido tem `pending` na coluna (`expired` nunca é gravado) — então ele casa com o
  `WHERE` e é revogado. Ficou assim de propósito e não por acidente da tabela: quem revoga está
  dizendo "este convite não vale", e ele já não valia. O efeito colateral é que ele **sai** do
  filtro `expired` e **entra** no `revoked` depois disso, que é a leitura honesta do que houve.
- **`platform_admin` ganhou teste, e não só ausência no mapa.** A spec diz que ele não recebe
  nenhuma das duas; ficou `test_platform_admin_nao_convida_nem_le_convite_do_cliente`, porque a
  decisão é contraintuitiva (o instinto de quem refatora é "admin pode tudo") e porque o 403 dele
  vem de um caminho específico: o `require_permission` **afrouxa** pra `platform_admin` somando
  as permissões de plataforma em qualquer `orgId`, então ele é negado por o mapa não lhe dar
  `invitations.*` — e não por não alcançar o tenant. Sem o teste, dar-lhe a capability "pra
  destravar a tela da Widelab" seria uma linha que ninguém barraria.
- **A afirmação de "Sem migration" se sustentou, mas a de `alembic check` limpo não — e já era
  falsa quando foi escrita.** Nenhum model e nenhuma migration foram tocados: `permissions` é
  código, o enum já tinha `revoked`, e o `CHECK` gerado sai de `ROLES_BY_ORGANIZATION_TYPE`, que
  esta spec **não** mexeu (mexeu em `PERMISSIONS_BY_ROLE`, que o banco não conhece). Logo o
  `alembic check` responde hoje exatamente o que respondia antes desta entrega — e o que ele
  responde são os **seis** `remove_fk` que a `10` documentou, não silêncio. A frase "o `alembic
  check` continua limpo", na seção `Sem migration` acima, repete o engano que a seção `Sem
  migration` da `09` cometeu; fica registrada como errada em vez de editada.
- **`partner_admin` não ganhou rota, teste de rota nova nem `if` em lugar nenhum** — só as duas
  linhas de `frozenset`, como a spec previa. O que o teste ponta a ponta mostrou é que o resto já
  estava de pé: o convite nasce, o aceite cria o `membership(partner_operator)` e a persona
  resolve pra `partner` sem uma linha de código específica de Parceiro. O `CHECK` do banco barra
  convidar `hr` pra um Parceiro; a aplicação devolve 422 antes, e as duas coisas têm teste
  separado — a aplicação explica, o banco impede.
- **O que a spec chamou de "três rotas de convite" são três, mas a de listar nasceu com um
  default opinativo.** Sem `?status=`, a rota devolve **só** os pendentes. Está no texto da spec,
  mas vale registrar que isso torna `GET .../convites` uma resposta *incompleta* por padrão: quem
  for montar a tela de gestão (spec de frontend) precisa saber que o histórico existe e se pede
  explicitamente, senão vai concluir que revogar apaga a linha — e não apaga, a revogação é soft.
- **Não há teste de paginação de verdade** (segunda página, `page_size` no limite). A rota herda o
  `get_page_params` e o `PageResponse.of` que as `03`/`04` já usam, e nenhum critério da spec
  pedia — mas nenhuma das listagens do `access` tem esse teste, e é uma lacuna do conjunto, não
  desta rota. Candidato a uma varredura quando a spec de CI passar por aqui.
