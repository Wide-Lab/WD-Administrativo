# 06 — Convites e onboarding

**Estado:** ✅ implementada (2026-07-16). Fecha a fase 1 do backend. Ver `Como ficou` no fim.
**Depende de:** `backend/02-identidade-e-sessao.md`, `backend/03-organizacoes-e-tenancy.md`,
`backend/04-membros-e-autorizacao.md`.
**Entrega:** os dois fluxos de entrada de gente no sistema — **Colaborador convidado** por
uma Empresa e **Parceiro auto-cadastrado** — mais o vínculo do Parceiro a uma Empresa.

## Objetivo

Como uma pessoa passa a ter login e vínculo. São dois caminhos deliberadamente diferentes,
que a `00-visao-geral.md` pediu pra separar de "membros":

- **Colaborador / staff da Empresa:** não se auto-cadastra. É **convidado** por quem tem
  `company_admin`/`hr`, com um papel já definido. Aceita o convite e define a senha.
- **Parceiro:** **se cadastra uma vez** (auto-registro cria a organização `partner` + o
  primeiro `partner_admin`), e depois é **associado** a Empresas por convênio.

## Fora de escopo

- Recuperação de senha ("esqueci") — spec própria futura (ver spec 02).
- Aprovação/curadoria de Parceiros pela plataforma antes de operar — se for necessário um
  gate, entra como status do convênio; o fluxo de aprovação em si é spec futura.

## Modelo

`invitations`

| coluna | tipo | nota |
|---|---|---|
| `id` | UUID (PK) | |
| `email` | CITEXT | |
| `organization_id` | UUID → `organizations` | pra qual org o convite dá vínculo |
| `role` | enum | papel que o vínculo terá ao aceitar |
| `token` | text, único | opaco, uso único |
| `status` | enum `pending`/`accepted`/`revoked`/`expired` | |
| `expires_at` | timestamptz | |
| `invited_by` | UUID → `users` | |
| `created_at` | timestamptz | |

## Fluxo A — Colaborador convidado

1. `POST /api/organizacoes/{orgId}/convites` (`company_admin`/`hr`) `{email, role}` na Empresa
   `{orgId}` → cria `invitation` pending com token e expiração; dispara e-mail (envio via
   porta em `core`; o provedor concreto é detalhe de infra, não desta spec).
2. `GET /api/convites/{token}` (público) → dados públicos mínimos pra tela de aceite (nome da
   Empresa, e-mail, papel). 404/410 se inválido/expirado.
3. `POST /api/convites/{token}/aceitar` `{name?, password}`:
   - se **não** existe `user` pro e-mail → cria via porta `UserDirectory` (definida em `core`,
     implementada por `auth`) e define a senha;
   - se **já** existe → apenas cria o `membership`;
   - cria o `membership (user, organization, role)`, marca o convite `accepted`, emite sessão.
   Idempotente por token: reusar um token já aceito não cria vínculo duplicado.

## Fluxo B — Parceiro auto-cadastrado

1. `POST /api/parceiros/cadastro` `{company_name, document?, admin: {name, email, password}}`
   (rota pública) → numa transação: cria `organization(type=partner)`, cria o `user` (via
   `UserDirectory`) e o `membership(partner_admin)`, emite sessão. E-mail duplicado → 409.
2. A associação a uma Empresa é o convênio da spec 03: `company_admin` faz
   `POST /api/organizacoes/{orgId}/convenios {partner_id}`. Alternativamente, uma Empresa pode **convidar** um
   Parceiro que ainda não existe reusando o Fluxo A com `organization` do tipo convite de
   parceria — decidir na implementação; o mínimo desta spec é auto-registro + associação por
   convênio.

## Regras de segurança

- Token opaco (ex.: 32 bytes url-safe), **uso único**, expira (default 7 dias).
- Aceitar convite não revela se o e-mail já tinha conta (resposta uniforme).
- `POST /api/parceiros/cadastro` e `aceitar` respeitam a mesma política de senha do login (spec 02).
- Convite é escopado à organização de quem convida; `hr` de uma Empresa não convida pra outra.

## Critérios de aceite

1. Convite → aceite cria exatamente um `user` (se novo) e um `membership` com o papel do
   convite; reaceitar o mesmo token não duplica nada e não reabre sessão indevidamente.
2. Convite expirado ou revogado recusa o aceite (410) e não cria vínculo.
3. `POST /api/parceiros/cadastro` cria org + admin + sessão numa transação atômica; e-mail
   repetido dá 409 sem criar organização órfã.
4. Um `hr` não consegue convidar para uma organização que não é a sua (403).
5. Criação de usuário no onboarding passa pela porta `UserDirectory`, sem `onboarding`
   importar `auth` diretamente.

## Como ficou

Os cinco critérios batem e foram observados rodando contra o Postgres real (num banco
descartável, `spec06`, no container do projeto), incluindo os 401, 403, 409, 410 e 422. O que a
implementação decidiu e a spec não previa:

- **O onboarding não é um módulo `onboarding`: mora dentro do `access`.** O critério 5 fala em
  "`onboarding` importar `auth`", o que sugere um módulo próprio, mas o `CLAUDE.md` já
  declarava o onboarding como um dos eixos do `access`, e a `00-visao-geral.md` põe o kernel em
  dois módulos, não três. Um terceiro módulo só pra convite duplicaria `organizations` e
  `memberships` do lado de lá ou o faria importar `access` — módulo importando módulo, o que o
  seam de extração proíbe. O que o critério 5 protege de verdade (não importar `auth`) foi
  verificado e vale: `grep` por `modules.auth` em `src/modules/access/` não acha nada.
- **A atomicidade do Fluxo B não vem de um `try`: vem da sessão compartilhada.** É o achado
  estrutural desta spec. `organizations`/`memberships` são do `access` e `users` é do `auth`,
  com unit of works diferentes — se o `UserDirectory` abrisse sessão própria, seriam duas
  transações e o critério 3 seria impossível de cumprir. Como `get_session` é uma dependency do
  FastAPI e é **cacheada por requisição**, a uow e a porta recebem a *mesma* `AsyncSession`: um
  `commit` cobre os três `INSERT`. Verificado de propósito, e não por sorte: um gatilho
  temporário no `users` fez o `INSERT` explodir **depois** de a organização já existir, e a
  organização não sobreviveu. Sem isso, o teste de e-mail duplicado passaria pela pré-checagem
  e nunca exercitaria o rollback — teria dado falso verde.
- **A porta `UserDirectory` fez o `auth` chegar a duas linhas no `mount_routes`, e a spec 02
  estava errada ao chamar o `UserReader` de "o único caso".** Não é: faltava o outro lado do
  verbo. `UserReader` lê identidade (pro `current_user`), `UserDirectory` a cria (pro
  onboarding). O `access` **não** cresceu — segue nas quatro linhas que a spec 05 chamou de
  teto, e o teto se sustentou.
- **`create` da porta recebe a senha em claro, não um hash.** O `access` até poderia hashear (o
  `hash_password` está no `core`), mas quem decide como uma senha é guardada tem que ser o dono
  da identidade — um `CentralSsoUserDirectory` futuro recusaria a senha em vez de guardá-la, e
  o `access` não precisa saber a diferença.
- **`expired` está no enum e nunca é gravado.** A spec declara os quatro status, mas quem sabe
  se um convite venceu é `expires_at` comparado ao agora, e não uma coluna: gravar exigiria um
  cron pra manter a coluna honesta, e até ele rodar um convite vencido responderia `pending` —
  duas fontes da verdade divergindo justo no instante que importa. `effective_status` deriva.
  Verificado: um convite com `expires_at` no passado segue `pending` no banco e o aceite
  responde 410 mesmo assim.
- **Reaceitar um token já aceito responde 410, não 200.** "Idempotente por token" (Fluxo A, item
  3) daria pra ler como "responde sucesso e não faz nada", mas o critério 1 cobra "não reabre
  sessão indevidamente" — e as duas leituras se encontram no 410: nada é criado *e* nenhuma
  sessão sai. Token é de uso único; um token gasto é um recurso que existiu e não vale mais,
  que é exatamente o que 410 quer dizer.
- **O uso único é um `UPDATE ... WHERE status = 'pending'`, não um `if`.** Ler o status e depois
  gravar deixaria dois aceites simultâneos do mesmo token passarem os dois pela checagem e
  criarem dois vínculos. O `UPDATE` condicional faz o banco decidir quem chegou primeiro; o
  segundo recebe `False` e leva 410.
- **A senha do corpo é ignorada quando a conta já existe, e isso é segurança, não economia.** A
  spec já mandava ("se já existe → apenas cria o `membership`"), mas vale registrar o porquê:
  se o aceite definisse a senha, convidar um e-mail já cadastrado viraria um caminho de
  redefinição de senha de conta alheia. Verificado: depois do aceite, a Ana continua entrando
  com a senha antiga e a senha mandada no aceite não funciona.
- **`name` é opcional e, faltando, o nome sai do local-part do e-mail.** Exigir `name` só quando
  o usuário não existe responderia 422 exatamente nos e-mails sem conta — o 422 viraria um
  oráculo de "esta pessoa já é cadastrada", furando a resposta uniforme que a spec pede. O
  fallback é feio e a pessoa troca depois; o vazamento não teria conserto.
- **A resposta do aceite é 200 sem corpo**, como o `POST /api/auth/login` (spec 02): a
  identidade vem do `GET /api/me`, e devolvê-la aqui seria uma segunda fonte da verdade. Os dois
  caminhos (conta nova e conta existente) respondem byte a byte igual — verificado.
- **`InvitationResponse` não devolve o `token`.** Ele é credencial e sai por e-mail, pro
  convidado. Devolvê-lo a quem convidou deixaria um `hr` aceitar no lugar da pessoa, e o e-mail
  deixaria de provar controle da caixa.
- **O token é gravado em claro, como a tabela da spec manda** (`token` text, único). Guardar só
  o hash seria mais seguro — um vazamento do banco expõe convites pendentes —, mas a coluna é
  contrato da spec e o risco é limitado (7 dias, e só vira senha pra quem ainda não tem conta).
  Fica **registrado como dívida**, não corrigido em silêncio.
- **A porta de e-mail (`core/notifications/`) não ganha linha no `mount_routes`**, diferente de
  todas as outras portas do `core`: e-mail é infra, não tabela de um módulo, então não há módulo
  pra registrar a implementação. O default é um `LoggingEmailSender` que escreve a mensagem no
  log — o fluxo funciona fim a fim em dev, com o link de aceite saindo no log, e trocar por
  SES/SMTP é registrar outra fábrica. A spec deixou o provedor concreto explicitamente de fora.
- **O e-mail sai depois do `commit`, de propósito.** Um e-mail que sai e uma transação que volta
  atrás deixariam um token vivo na caixa de alguém sem linha no banco. O contrário — commit
  feito e e-mail que falha — é recuperável reenviando.
- **`invitations` repete a FK composta + `CHECK` gerado de `memberships`**, e a `role_check_sql()`
  serve as duas sem parametrização porque nomeiam as colunas igual. Não é economia: um convite é
  um vínculo que ainda não aconteceu, e sem o CHECK aqui daria pra convidar um `hr` pra um
  Parceiro e só descobrir no aceite — o erro cairia na cara do convidado, não na de quem
  convidou errado. Verificado por `psql`, por fora da aplicação: o CHECK barra o papel errado e a
  FK composta barra mentir no `organization_type`.
- **O furo do e-mail duplicado que a spec 03 registrou foi fechado só no caminho novo.** O
  `SqlAlchemyUserDirectory.create` traduz `IntegrityError` → `ConflictError` no `flush`, que é o
  que dá o 409 do critério 3. **O `UserRepository.create` do `auth` continua com o furo** (um
  e-mail duplicado por ali ainda vira 500): mexer nele segue sendo escopo da spec do `auth`, e
  hoje só a CLI o alcança, que já checa antes.
- **`hr` recebe `invitations.write` e continua sem `members.write`**, e é isso que separa os dois
  papéis nesta fase: o RH decide quem entra, o `company_admin` mexe em quem já entrou.
- **`platform_admin` não recebe `invitations.write`**, pelo mesmo motivo do `agreements.write`
  (spec 04): convidar é ato da Empresa. A plataforma provisiona tenant e conserta vínculo pela
  CLI; não chama gente pro time do cliente.
- **O Fluxo B ficou no mínimo que a spec pediu** — auto-registro + associação por convênio. A
  spec deixava em aberto ("decidir na implementação") convidar um Parceiro inexistente reusando
  o Fluxo A; não foi feito, porque o convênio já resolve a associação e um "convite de
  parceria" é outro fluxo, com outra tela e outro aceite. Se fizer falta, é spec nova.
- **`company_name` nomeia o Parceiro no payload do auto-cadastro**, o que é confuso num domínio
  onde `company` é um tipo de organização *diferente* de `partner`. Foi mantido porque o payload
  é contrato da spec. Candidato a renomear (`nome`/`razao_social`) na spec do frontend que
  consumir a rota — aí o custo é um campo, não uma migração.

### O que esta spec **não** entregou, e alguém vai sentir falta

Nenhum dos dois estava nos critérios de aceite nem no `Fora de escopo` — são buracos do texto
original, não do código, e por isso **não** foram preenchidos por conta própria:

- **Não há rota pra revogar nem pra listar convites.** O modelo tem `revoked` e o critério 2
  cobra que um convite revogado seja recusado (e é — verificado), mas nenhuma rota grava esse
  status: hoje, revogar um convite mandado por engano é `UPDATE` no `psql`, e quem convidou não
  tem como ver o que está pendente. É a lacuna mais provável de doer primeiro.
- **Um Parceiro não consegue crescer.** Só `company_admin`/`hr` têm `invitations.write`, como a
  spec desenhou (Fluxo A é explicitamente "Colaborador / staff da **Empresa**"). Como o Fluxo B
  cria só o primeiro `partner_admin`, não existe caminho de produto pra um segundo membro de um
  Parceiro — `partner_operator` só nasce pela CLI. Dar `invitations.write` ao `partner_admin`
  seria uma linha num `frozenset`, e o `CHECK` do banco já aceitaria os papéis de Parceiro; não
  foi feito porque é escopo que a spec não pediu.

- **Sem testes automatizados** — o backend segue sem framework de teste e esta spec não cita
  testes; a verificação foi por `curl` e `psql`, mais o gatilho temporário do rollback. **A
  dívida que as specs 03/04/05 registram continua de pé e agora é a mais cara da fase 1**: o uso
  único do token, a resposta uniforme e a atomicidade do auto-cadastro são exatamente o tipo de
  propriedade que some numa refatoração sem ninguém notar, e que um teste barato prenderia. Uma
  spec de infra de teste (`pytest` + Postgres efêmero) deixou de ser "o próximo candidato óbvio"
  e virou o pré-requisito honesto da fase 2.
