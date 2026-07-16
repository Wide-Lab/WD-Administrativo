# 07 — Testes automatizados

**Estado:** ✅ implementada (`234a90e`, 2026-07-16) — 69 testes, ver `Como ficou` no fim.
**Depende de:** `backend/01-fundacao.md` (scaffold e tooling). Prende o que as
`backend/02`–`06` já entregaram — todas implementadas.
**Entrega:** `pytest` + Postgres efêmero (testcontainers) rodando contra a app de verdade, a
suíte que prende as invariantes que as `Como ficou` das `03`–`06` nomearam como dívida, e a
regra que faz teste deixar de ser opcional no backend.

## Objetivo

Parar de descobrir por refatoração que o multi-tenant abriu. Hoje o backend nega de verdade —
403 em tenant sem vínculo, em permissão faltante e em módulo não contratado — mas isso foi
verificado **uma vez**, à mão, por `curl` e `psql`, e não se repete. Esta spec transforma essa
verificação manual em algo que roda em segundos e quebra quando alguém desfaz a garantia sem
querer.

Quatro specs seguidas (`03`, `04`, `05`, `06`) fecharam registrando a mesma dívida, cada uma
mais cara que a anterior: a `06` a chamou de "a mais cara da fase 1" e de "pré-requisito honesto
da fase 2". Esta spec é a cobrança dela.

## Fora de escopo

- **Frontend.** A dívida de teste do frontend é real e está registrada (`00-visao-geral.md`: a
  casca, os guards, o `Can` e o seletor da `frontend/05` foram vistos a olho uma vez; o
  `lib/last-org.ts`, que engole falha de `localStorage`, não tem rede nenhuma). Ela **continua
  aberta** e ganha spec própria — a decisão de escopo aqui é do usuário, não um esquecimento. O
  `frontend/01-fundacao.md` decidiu Vitest só pra libs puras, e esta spec **não** mexe nisso.
- **CI.** Rodar a suíte a cada push é a spec seguinte. Sem CI, a rede depende de `uv run pytest`
  antes do commit — o que já é infinitamente mais do que existe hoje. Separada porque runner,
  segredo e Docker-no-CI são problema de infra, não de teste.
- **Cobertura retroativa exaustiva das `02`–`06`.** A suíte prende as invariantes que as próprias
  specs nomearam (tabela abaixo), não cada caminho de cada rota. Perseguir 100% agora atrasaria a
  fase 2 pra proteger getter.
- **Gate de cobertura (`--cov-fail-under`).** Percentual vira alvo e se atinge escrevendo teste
  ruim. O que vale é a tabela de invariantes, que é nominal.
- **E2E de browser (Playwright).** Outra pirâmide, outra spec.
- **Teste de carga/performance.** Não é a pergunta desta fase.

## Postgres real, não mock nem SQLite

Decisão travada, porque ela decide se a suíte vale alguma coisa: **as invariantes deste backend
moram no banco.** Um repositório fake ou um SQLite passariam verdes enquanto testam nada do que
importa:

| Invariante                                            | Onde vive                                        |
| ----------------------------------------------------- | ------------------------------------------------ |
| papel só vale no tipo de organização certo            | `CHECK` **gerado** de `ROLES_BY_ORGANIZATION_TYPE` |
| não dá pra mentir o `organization_type` de um vínculo | FK composta → `organizations(id, type)`          |
| tipo de organização é imutável sob convênio           | FK composta (`backend/03`)                       |
| e-mail é case-insensitive                             | `CITEXT`                                         |
| auto-cadastro de Parceiro é atômico                   | transação real                                   |

Nenhuma delas é um `if` em Python. Mockar o repositório testaria o mock; SQLite não tem `CITEXT`
nem os `CHECK` que geramos. **A suíte fala com Postgres de verdade, com o schema criado por
`alembic upgrade head`** — o que, de quebra, prende as migrations: a `04` registrou que
`fk_memberships_user` existe só na migration e que um `autogenerate` futuro vai querer dropá-la.
Uma suíte que migra do zero é onde isso aparece.

## A stack

| Peça                       | Papel                                        |
| -------------------------- | -------------------------------------------- |
| `pytest`                   | runner                                       |
| `pytest-asyncio`           | a app é async ponta a ponta                  |
| `httpx` + `ASGITransport`  | requisição na app **sem** subir servidor/rede |
| `testcontainers[postgres]` | um Postgres descartável por sessão           |

Tudo em `[dependency-groups] dev` do `pyproject.toml`, junto de `mypy` e `ruff`.

**Por que testcontainers e não um serviço no `docker-compose`:** o compose já expõe um Postgres
numa porta fixa, e a máquina de dev **já tem outro projeto em `localhost:5432`**. Um serviço de
teste em porta fixa é colisão esperando acontecer, e a falha é silenciosa e cara — a suíte roda
migration no banco errado. Testcontainers sobe em porta efêmera e a devolve pro processo, então
"a suíte nunca aponta pro banco errado" vira **estrutura**, não regra pra alguém lembrar.

**Custo aceito:** a suíte exige Docker rodando (Docker Desktop, no Windows da casa). Sem Docker,
`pytest` falha na hora com mensagem clara em vez de tentar um banco qualquer.

## A suíte nunca herda `DATABASE_URL`

O `Config` (`core/config.py`) é `BaseSettings` sem `env_file`, e nada no Python carrega o `.env`
— ele chega na app só pelo `env_file:` do compose. Ou seja: `uv run pytest` nativo lê o que o
shell exportar. E o `backend/.env` deste repo aponta pra
`postgresql+asyncpg://postgres:postgres@localhost:5432/…`, que é **de outro projeto**.

Some a isso que `get_config()` e `get_database()` são os dois `@lru_cache(maxsize=1)`, e que
`src/main.py` faz `app = create_app()` no import — a primeira leitura de config acontece cedo e
congela.

Portanto, o `conftest.py` raiz, **antes de qualquer import de `src`**:

1. sobe o container e pega a URL efêmera;
2. **sobrescreve** `os.environ["DATABASE_URL"]` com ela — sobrescreve, não usa `setdefault`: o
   valor do shell é exatamente o perigo;
3. fixa `JWT_SECRET_KEY` de teste;
4. limpa os dois `lru_cache` (`get_config.cache_clear()`, `get_database.cache_clear()`).

Um `DATABASE_URL` exportado no shell apontando pro banco errado **não** pode mudar o alvo da
suíte. Isso é o critério de aceite 2, e é a razão de ele existir.

## Estrutura

```
backend/tests/
  conftest.py            # container, migrations, engine, limpeza, client
  factories.py           # make_user / make_organization / make_membership / …
  unit/
    access/test_permissions.py     # o mapa papel→permissão, sem banco
  integration/
    auth/test_login.py
    access/test_tenancy.py
    access/test_authz.py
    access/test_entitlements.py
    access/test_invitations.py
    test_migrations.py
```

`unit/` é pra regra pura (`permissions.py` é `frozenset` e função — não precisa de banco e não
deve pagar por um). `integration/` fala com a app e com o Postgres. A divisão não é cerimônia: o
`unit/` roda em milissegundos e é onde o mapa papel→permissão fica preso.

## Isolamento entre testes

**Um container por sessão**, `alembic upgrade head` uma vez, e **`TRUNCATE` das tabelas entre
cada teste**, com o *reseed* da organização `platform` que a migration `0002` semeia.

**Por que `TRUNCATE` e não uma transação externa com rollback:** o truque de embrulhar cada teste
numa transação e desfazê-la no fim é mais rápido, mas mascara exatamente o que a `06` precisa que
seja testado — **a atomicidade do auto-cadastro de Parceiro**. Um teste que verifica que uma falha
não deixa organização órfã precisa de commit e rollback **de verdade**, não de savepoint aninhado
dentro do harness. Velocidade aqui vale menos que poder testar a propriedade cara.

O reseed é obrigatório porque `TRUNCATE` leva junto a organização `platform`
(`01890000-0000-7000-8000-000000000001`), da qual todo teste de `platform_admin` depende.

## Fixtures — o contrato

O formato importa, porque é o que todo teste futuro vai usar:

```python
@pytest.fixture(scope="session")
async def database_url() -> AsyncIterator[str]: ...
    # sobe o container, migra, devolve a URL efêmera

@pytest.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]: ...
    # TRUNCATE + reseed da org platform, antes de cada teste

@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]: ...
    # httpx sobre ASGITransport, sem rede

@pytest.fixture
async def como() -> Callable[..., Awaitable[AsyncClient]]: ...
    # como(role="hr", org=empresa) -> client já com cookie de sessão
```

A fixture que decide a ergonomia da suíte é a última. A pergunta que este backend responde é
sempre a mesma — *"papel X, na organização Y, batendo no endpoint Z: 200 ou 403?"* — e sem um
atalho pra "me dê um cliente autenticado como `hr` na Acme", cada teste vira quinze linhas de
setup e ninguém escreve o segundo. Ela cria usuário, organização e vínculo pelas factories, faz
o login de verdade e devolve o cliente com o cookie.

## O que a suíte prende

Nominal, derivado das `Como ficou` — cada linha é uma dívida que uma spec registrou:

| Spec | Invariante                                                                                   |
| ---- | -------------------------------------------------------------------------------------------- |
| `02` | login errado responde 401 **uniforme** (não revela se o e-mail existe); senha é Argon2id; `/api/me` sem cookie é 401 |
| `03` | 403 em tenant sem vínculo; `type` de organização não muda sob convênio; convênio recusa lado de tipo errado |
| `04` | `CHECK` recusa `hr` num `partner`; FK composta recusa `organization_type` mentido; `require_permission` 200/403; `platform_admin` alcança tenant sem vínculo; `PATCH` de vínculo de outra org é **404, não 403** |
| `05` | `require_module` nega por padrão; **não afrouxa nem pra `platform_admin`**; `/me` devolve `modules` do tenant |
| `06` | token de convite é **uso único**; aceite responde **uniforme**; TTL de 7 dias expira; auto-cadastro de Parceiro que falha **não deixa organização órfã** |
| —    | `alembic upgrade head` sobe do zero num banco vazio                                          |

O `platform_admin` da `05` e o 404 da `04` estão aqui de propósito: são decisões **contraintuitivas**
(o instinto de quem refatora é "admin pode tudo" e "sem acesso é 403"), e é por isso que somem
sozinhas.

## A regra que fica

Infra de teste sem regra vira `tests/` com três arquivos de 2026. O que impede a dívida de voltar
não é esta spec — é o que roda **toda vez**. Duas edições, parte da entrega:

**`CLAUDE.md`, em "Convenções que não se negociam":**

> **Teste não é opcional no backend.** Todo critério de aceite que se observa por requisição ou
> por SQL vem com teste em `backend/tests/` **na mesma entrega**, não em spec futura. Fechar sem
> teste é exceção justificada no `Como ficou` — não o default, como foi nas `03`–`06`.

**`.claude/skills/implementar-spec/SKILL.md`, passo 4** — hoje diz *"Specs que citam testes:
escreva os casos citados"*, e esse **opt-in é a causa raiz**: as `03`–`06` não citaram testes,
então não tiveram. Vira:

> **Backend: todo critério de aceite testável vira teste em `backend/tests/` e roda com `uv run
> pytest`, na mesma entrega.** `curl` uma vez prova que funcionou hoje; teste prova que continua
> funcionando. Frontend: specs que citam testes, escreva os casos citados antes de `npm run test`.

**`.claude/skills/nova-spec/SKILL.md`**, em "Critérios de aceite": critério de backend deve ser
escrito de forma **observável por teste automatizado** — é o que torna a regra acima exequível
sem renegociar em cada spec.

## Comandos

| De `backend/`, via `uv run` |                                    |
| --------------------------- | ---------------------------------- |
| `pytest`                    | a suíte (exige Docker rodando)     |
| `pytest tests/unit`         | só a regra pura, sem Docker        |
| `pytest -k entitlement`     | um recorte                         |

Entra na tabela de comandos do `CLAUDE.md`.

`mypy` passa a rodar em `src` **e** `tests`, com `disallow_untyped_defs` mantido. O custo é um
`-> None` por teste; o ganho é fixture com tipo errado quebrando no typecheck e não em runtime.

## Critérios de aceite

1. `uv run pytest` de `backend/`, com Docker rodando, fica **verde sem nenhum setup manual** — sem
   criar banco, sem rodar migration à mão, sem `.env`.
2. Com `DATABASE_URL` **exportado no shell apontando pra outro banco** (ex.: o `localhost:5432` do
   `.env`), a suíte roda contra o container mesmo assim, e aquele banco fica **intocado** —
   verificado olhando que nenhuma tabela foi criada lá.
3. O schema da suíte sai de `alembic upgrade head` num banco vazio; derrubar uma migration faz a
   suíte falhar.
4. Existe teste **passando** pra cada linha da tabela "O que a suíte prende", incluindo: `hr` num
   `partner` viola o `CHECK`; `require_module` nega pra `platform_admin`; token de convite usado
   duas vezes falha na segunda; auto-cadastro de Parceiro que falha no meio não deixa organização
   órfã.
5. A suíte é isolada: rodar `uv run pytest` duas vezes seguidas dá o mesmo resultado, e qualquer
   teste sozinho (`pytest tests/integration/access/test_authz.py::test_x`) passa.
6. `uv run ruff check .` e `uv run mypy src tests` passam, com o código de teste incluído.
7. `CLAUDE.md`, `implementar-spec` e `nova-spec` carregam a regra da seção "A regra que fica", e a
   tabela de comandos do `CLAUDE.md` tem `pytest`.
8. Sem Docker, `uv run pytest` falha com mensagem dizendo que Docker é necessário — não com
   `ConnectionRefused` contra um banco qualquer.

## Como ficou

69 testes, ~13s a suíte inteira e 0,04s o `tests/unit`. A stack, o isolamento por `TRUNCATE`, o
Postgres real e a tabela de invariantes saíram como o texto pediu. O que divergiu:

**O `clean_database` mora em `tests/integration/conftest.py`, não no raiz.** A spec o desenhou
`autouse` no `conftest.py` raiz, e as duas coisas não cabem juntas: `autouse` no raiz vale
também pra `tests/unit/`, e aí `pytest tests/unit` passaria a exigir Docker pra testar um
`frozenset` — contradizendo a própria spec, que promete o `unit/` "sem Docker" na tabela de
comandos e o descreve rodando em milissegundos. O resto do contrato de fixtures (`database_url`,
`client`, `como`) ficou no raiz como escrito. A dependência de banco para nesta porta, e é o que
mantém as duas promessas.

**"Antes de qualquer import de `src`" virou "antes de qualquer import de `src.main`".** A spec
pediu o setup de env no topo do `conftest.py` raiz, o que obrigaria o container a subir no import
— de novo, Docker pro `unit/`. Verificando na prática, **só `src/main.py` lê config no import**
(o `app = create_app()`); todo o resto de `src` só define. Então o env é sobrescrito na fixture
`database_url` e `src.main` é importado tarde, dentro de `_new_client()`. O critério 2 foi
verificado de verdade contra um segundo Postgres descartável em `localhost:55432` com
`DATABASE_URL` **exportado** apontando pra ele: a suíte ficou verde contra o container e o banco
isca terminou sem uma tabela sequer — nem `alembic_version`. A isca foi um container próprio, e
não o `localhost:5432` do `.env`, justamente porque aquela porta é de outro projeto: verificar
"o banco fica intocado" apontando pro banco de outro projeto é o acidente que o critério existe
pra prevenir.

**O `get_jwt_encoder` também tem `cache_clear()`.** A spec nomeia dois `lru_cache`; são três, e o
terceiro guarda o segredo de sessão. Nenhum dos três chega a ser populado antes da fixture hoje,
mas deixar um de fora seria confiar em ordem de import pra segurança.

**`require_module` só é testável por uma rota de prova, e isso é achado da implementação.**
`refeicoes` e `frota` são descritores **sem `router`** — ou seja, hoje **não existe um único
endpoint atrás do `require_module` no app**, e a invariante mais cara da `05` ("não afrouxa nem
pra `platform_admin`") não tinha onde ser perguntada. A fixture `rota_de_prova`
(`test_entitlements.py`) pendura um endpoint mínimo atrás do guard **real**, com a chave real
`refeicoes`. Ela não passa por `mount_module` de propósito: `register_module` escreve num dict
global que vive o processo inteiro, e o módulo de prova vazaria pro catálogo do `GET /modulos` de
outros testes. **Consequência: `mount_module` — o prefixo e o guard automáticos — segue sem
teste.** Ele só é testável honestamente quando o primeiro app de negócio existir; é dívida da
fase 2, e a rota de prova some junto.

**A atomicidade do Parceiro exigiu `monkeypatch`, e é o teste mais instrutivo da suíte.** O
`RegisterPartnerUseCase` confere o e-mail **antes** de criar a organização, então o caminho comum
nunca chega a escrever — um teste que só mandasse e-mail duplicado passaria verde sem tocar na
transação, que é justamente o que a `06` quer preso. O teste apaga só a conferência prévia
(`find_id_by_email` → `None`), reproduzindo a corrida que o docstring do use case descreve, e aí
a organização **já foi inserida** quando o `users` estoura. É esse teste que quebra se alguém der
uma uow própria ao `UserDirectory` — e é ele que justifica o `TRUNCATE` no lugar do rollback.

**O harness limpa por sessão, não por `engine.begin()`.** O `Database` do `core` expõe a engine
pela porta `Engine`, que só sabe `dispose()` — o `mypy` acusou. A limpeza entra pela mesma porta
que a app usa pra escrever, o que é mais fiel de qualquer forma.

**Três ajustes de mecânica que o texto não previa e valem pro próximo:** o cliente httpx fala em
`https://testserver`, porque o cookie de sessão nasce `Secure` e sobre `http` o jar o descartaria
em silêncio (todo teste autenticado daria 401 pelo motivo errado); `alembic upgrade head` roda em
`asyncio.to_thread`, porque `migrations/env.py` faz `asyncio.run()` e estouraria dentro da
fixture async; e o `mypy` precisou de `explicit_package_bases`, porque dois `conftest.py` sem raiz
de pacote viram "módulo duplicado" e ele desiste antes de checar qualquer coisa.

**O critério 8 falhou na primeira tentativa, e o conserto é a lição:** `PostgresContainer(...)` já
fala com o daemon **na construção**, não no `start()`. Com o `try` só no `start()`, quem estivesse
sem Docker recebia um dump de HTML de proxy de 10KB. Verificado com `DOCKER_HOST` apontando pra
uma porta morta.

**Sobre o escopo da tabela.** Cada linha de "O que a suíte prende" tem teste passando, mas a suíte
tem mais do que a tabela: entrou o **par positivo** de cada negação (o 200 que faz o 403 significar
alguma coisa — um teste de 403 sozinho passa com a rota quebrada), os 401 sem sessão, e as
invariantes de banco da seção "Postgres real" (CITEXT no login, `platform` singleton). Não entrou
cobertura de caminho de rota além disso, como o "Fora de escopo" pede.

**O que segue aberto, e agora com nome:** CI (spec seguinte — sem ela, a rede depende de `uv run
pytest` antes do commit), a dívida de teste do **frontend**, `mount_module` sem teste (fase 2), e
o `pytest tests/unit` ser a única parte que roda sem Docker — o custo aceito que a spec já
declarava.
