# 08 — Gestão de convites (listar, revogar, Parceiro convida)

**Estado:** ✅ implementada (2026-07-20) — fecha os três buracos que a `06` deixou de propósito.
235 testes (216 + 19), sem migration. Ver `Como ficou` no fim.
**Depende de:** `backend/06-convites-e-onboarding.md` (o modelo `invitations`, o aceite, o
mapa de papéis/permissões), `backend/07-testes.md` (a suíte que os critérios abaixo estendem).
**Entrega:** as rotas de **listar** e **revogar** convite que faltaram à `06`, mais dar ao
`partner_admin` o direito de convidar — os três buracos que a `06` deixou de propósito e o
`00-visao-geral.md` registrou como spec nova.

## Objetivo

Fechar o que a `06` deixou aberto no próprio `Como ficou`: hoje quem convida **não vê o que
está pendente** e **revogar um convite mandado por engano é um `UPDATE` no `psql`**; e um
**Parceiro não cresce** — como o auto-cadastro só cria o primeiro `partner_admin` e só Empresa
convida, o segundo membro de um Parceiro só nasce pela CLI. Esta spec dá as rotas que faltam e
uma linha de permissão, sem tocar no fluxo de aceite nem no modelo.

## Fora de escopo

- **Frontend.** A tela de gestão de convites (listar/revogar na casca do Admin) e o **link pra
  `/parceiros/cadastro`** — o item que a `frontend/06` deixou "sem link em lugar nenhum" — são
  uma spec de frontend própria, como a `06` foi backend e frontend separados. Esta entrega são
  só as rotas e a regra de permissão; ficam **observáveis por teste** sem esperar UI.
- **Reenvio de convite.** Reemitir o e-mail de um convite pendente é conveniência, não lacuna
  de segurança nem de crescimento — se doer, é uma rota a mais depois. O caminho de hoje
  (revogar + convidar de novo) já resolve o convite mandado errado.
- **Notificar o convidado de que o convite foi revogado.** Um convite revogado já é recusado no
  aceite (410); avisar por e-mail é decisão de produto, spec futura.
- **Recuperação de senha e curadoria/aprovação de Parceiro** — seguem fora, como na `06`.
- **Bloquear convite duplicado** (segundo `pending` pro mesmo e-mail+org). Decidido **não**
  fazer: criar não checa duplicata hoje, o caminho limpo é revogar o antigo e reconvidar, e uma
  constraint de unicidade é escopo que nem a `06` nem esta spec pediram. Se fizer falta, é
  critério de uma spec futura.

## Sem migration

Nada aqui toca o schema. O enum `invitation_status` já tem `revoked` (migration `0005`), a
`InvitationResponse` já **não** devolve o `token` (`06`), e o `CHECK` gerado de `invitations`
já aceita os papéis de Parceiro (`ROLES_BY_ORGANIZATION_TYPE`). As permissões são código, não
banco. Logo: **nenhuma revisão de Alembic** — a suíte segue migrando de `alembic upgrade head`
e o `alembic check` continua limpo.

## Permissões

Uma capability nova e três linhas em `PERMISSIONS_BY_ROLE` (`access/domain/permissions.py`):

| Capability | Nova? | Quem recebe |
|---|---|---|
| `invitations.read` | **sim** | `company_admin`, `hr`, `partner_admin` |
| `invitations.write` | já existe | `company_admin`, `hr` — **e agora `partner_admin`** |

Por que uma `invitations.read` separada, e não reusar `invitations.write` pra listar: a `06`
já separou "quem decide quem entra" de "quem mexe em quem já entrou" (o `hr` tem
`invitations.write` e **não** `members.write`). Listar é leitura, e o par read/write espelha
`members.read`/`members.write` — o mesmo desenho, não um novo. Quem convida enxerga o que
convidou; ninguém a mais.

`partner_admin` ganha as **duas**: sem `write` ele não convida (o buraco do crescimento), e sem
`read` ele convidaria às cegas. `partner_operator` segue sem nenhuma — Parceiro cresce pela
mão do seu admin, como a Empresa. E o `CHECK` do banco já garante que um `partner_admin` só
consegue convidar papel de Parceiro: convidar um `hr` pra um `partner` é barrado no banco, não
na aplicação — a mesma divisão de trabalho da `06`.

`platform_admin` **não** ganha nenhuma das duas, pelo motivo da `06`: convidar é ato da
organização, não da Plataforma. A Widelab provisiona tenant e conserta vínculo pela CLI.

## Rotas

Ambas sob o tenant do path, atrás de `require_permission`, ao lado do
`POST /organizacoes/{orgId}/convites` que a `06` já entregou:

| Rota | Permissão | Resposta |
|---|---|---|
| `GET /api/organizacoes/{orgId}/convites` | `invitations.read` | `200` — página de `InvitationResponse` |
| `DELETE /api/organizacoes/{orgId}/convites/{id}` | `invitations.write` | `204` — sem corpo |

### Listar — `GET /api/organizacoes/{orgId}/convites`

- Paginada como `GET .../membros` e `.../modulos` (`PageResponse[InvitationResponse]`), escopada
  ao `organization_id` do path — convite de outra organização nunca aparece.
- **Nunca devolve o `token`.** A `InvitationResponse` já foi desenhada sem ele na `06`; é a
  mesma razão (o token é credencial, sai por e-mail pro convidado), e é o que impede quem
  convidou de aceitar no lugar da pessoa.
- **O `status` de cada item é o efetivo** (`effective_status(now)`), não a coluna crua: um
  convite cujo `expires_at` passou aparece como `expired`, não `pending`, sem nada ter gravado a
  coluna — a mesma verdade derivada que o aceite consulta. Isto **diverge** do
  `InvitationResponse.from_entity` atual, que copia `entity.status`; a listagem resolve o
  efetivo antes de montar a resposta.
- **Filtro opcional `?status=`** (`pending`/`accepted`/`revoked`/`expired`), aplicado sobre o
  status **efetivo**. **Sem** filtro, o default é `pending` — a pergunta que a rota responde
  primeiro é "o que ainda está de pé pra alguém aceitar"; o histórico se pede explicitamente.

### Revogar — `DELETE /api/organizacoes/{orgId}/convites/{id}`

Por que `DELETE` e não `PATCH` espelhando suspender/reativar convênio (`03`): revogar é
**terminal**. Um convite revogado não "reativa" — reconvidar é criar outro, com token novo. O
`DELETE` afirma um estado final, como o `DELETE .../modulos/{chave}` da `05`; e é **soft**
(grava `status = 'revoked'`, mantém a linha), não apaga: a linha é o registro de quem convidou
quem, e o aceite precisa dela pra recusar com 410.

**Por `id`, nunca por token** — o `id` é o que a listagem devolve; o token quem convidou não
tem (nem deve ter). Um `id` que existe mas é de **outra** organização responde **404, não
403**: mesma decisão do `PATCH .../membros/{id}` da `04` — 403 confirmaria que o convite existe,
e a resposta não pode virar oráculo.

O uso único segue o padrão da `06`: um **`UPDATE ... WHERE id = ? AND organization_id = ? AND
status = 'pending'`**, não um `if` sobre um status lido antes. É o banco que decide a corrida
(dois revogar simultâneos, ou revogar competindo com aceitar) — quem chega primeiro leva o
`pending`, o outro vê 0 linhas afetadas.

Estados e respostas:

| Estado do convite (coluna) | Resposta | Por quê |
|---|---|---|
| `pending` | `204` + grava `revoked` | o caso comum |
| `revoked` | `204` | idempotente — o `DELETE` afirma um estado já alcançado |
| `accepted` | **`409`** | vínculo já existe; tirar acesso é `members.write`, não revogar convite |
| não existe nesta org | `404` | não vaza existência (ver acima) |

O `409` do aceito é a decisão que separa esta rota de um `DELETE` idempotente puro: um convite
aceito **virou membro**, e revogá-lo não removeria o acesso — daria a falsa impressão de ter
removido. Quem quer tirar o acesso usa o `PATCH .../membros/{id}` da `04`.

## Parceiro cresce

Não há rota nova pro Parceiro convidar: ele usa **as mesmas** três rotas de convite, agora que
`partner_admin` tem `invitations.write`/`invitations.read`. `POST .../convites` na organização
`partner` cria o convite; o aceite (`06`) cria o `membership(partner_operator|partner_admin)`;
a persona resolve pra `PARTNER` como já resolve. O `CHECK` gerado barra papel de Empresa num
convite de Parceiro, então o caminho é seguro sem nenhuma regra a mais na aplicação.

## Testes — na mesma entrega

Todos os critérios abaixo são observáveis por requisição contra o Postgres real, então **viram
teste em `backend/tests/integration/access/test_invitations.py`** (o arquivo que a `07` já
criou), na mesma entrega — a regra do `CLAUDE.md`. O par positivo de cada negação entra junto
(o 204 que faz o 409 significar algo), como a `07` fixou.

## Critérios de aceite

1. `GET /api/organizacoes/{orgId}/convites` como `hr` ou `company_admin` devolve os convites
   **pendentes** da Empresa do path, paginado, e **nenhum item traz `token`**; um convite de
   outra organização não aparece na lista.
2. Um convite cujo `expires_at` já passou aparece na listagem com `status = "expired"` — e a
   coluna `status` no banco segue `pending` (a expiração é derivada, nada a gravou).
3. `GET .../convites?status=revoked` (e os demais valores) devolve só os convites cujo status
   **efetivo** é o pedido; sem o parâmetro, só os `pending`.
4. `DELETE /api/organizacoes/{orgId}/convites/{id}` como `hr`/`company_admin` sobre um convite
   pendente responde `204` e grava `status = 'revoked'`. Em seguida, `GET /api/convites/{token}`
   daquele convite responde `410` e `POST /api/convites/{token}/aceitar` é recusado com `410`
   sem criar vínculo — o ciclo que a `06` só fechava por `psql`, agora pela API.
5. `DELETE` sobre um convite **já aceito** responde `409` e o `membership` criado no aceite
   continua intacto. `DELETE` sobre um **já revogado** responde `204` (idempotente).
6. `GET` e `DELETE` de um `id` que existe mas pertence a **outra** organização respondem
   `404` (não `403`); sem sessão, `401`.
7. Um papel sem `invitations.read` (ex.: `finance`, `collaborator`, `partner_operator`) recebe
   `403` no `GET .../convites`; um sem `invitations.write` recebe `403` no `DELETE`.
8. `partner_admin` faz `POST /api/organizacoes/{orgId}/convites` na sua organização `partner`,
   o convidado aceita e vira `membership` de papel de Parceiro; um convite com papel de Empresa
   (`hr`) numa organização `partner` é recusado pelo `CHECK`. `partner_operator` recebe `403` ao
   tentar convidar.
9. Dois `DELETE` simultâneos do mesmo convite pendente não corrompem estado (o segundo é um
   no-op sobre `revoked`), e a revogação é um `UPDATE ... WHERE status = 'pending'`, não uma
   leitura seguida de escrita — verificável reproduzindo a corrida com o convite já não-pendente
   entre a leitura e a escrita.

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
  check` continua limpo", na seção `Sem migration` acima, repete o engano que o `Como ficou` da
  `09` cometeu; fica registrada como errada em vez de editada.
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
