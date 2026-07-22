# 07 — Testes automatizados — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

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
