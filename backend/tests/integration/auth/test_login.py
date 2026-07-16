"""O que a spec 02 registrou como dívida: o 401 uniforme, o Argon2id e o `/api/me` sem cookie."""

import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_config
from src.modules.auth.adapters.db.models import User as UserModel
from tests.factories import DEFAULT_PASSWORD, make_user


async def test_login_com_credencial_valida_entrega_o_cookie_de_sessao(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    user = await make_user(session, email="ana@widelab.com.br")

    response = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 200
    cookie = get_config().SESSION_COOKIE_NAME
    assert cookie in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()


async def test_login_errado_responde_401_uniforme(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """**Não revela se o e-mail existe.** As duas respostas têm que ser indistinguíveis: um
    corpo diferente pra "e-mail não existe" e pra "senha errada" transforma o login num oráculo
    de quem é cadastrado — e a enumeração de e-mails é o primeiro passo do ataque, não o
    último."""

    await make_user(session, email="existe@widelab.com.br")

    senha_errada = await client.post(
        "/api/auth/login",
        json={"email": "existe@widelab.com.br", "password": "senha-errada-mas-longa"},
    )
    email_inexistente = await client.post(
        "/api/auth/login",
        json={"email": "nao-existe@widelab.com.br", "password": "senha-errada-mas-longa"},
    )

    assert senha_errada.status_code == 401
    assert email_inexistente.status_code == 401
    assert senha_errada.json() == email_inexistente.json()
    assert get_config().SESSION_COOKIE_NAME not in senha_errada.cookies
    assert get_config().SESSION_COOKIE_NAME not in email_inexistente.cookies


async def test_usuario_sem_senha_definida_nao_loga(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """O convidado que ainda não aceitou tem `password_hash` nulo (spec 06). Ele não é um login
    aberto — e recusa pelo mesmo 401 uniforme."""

    user = await make_user(session, email="convidado@widelab.com.br", password=None)

    response = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 401


async def test_a_senha_e_argon2id_no_banco(session: AsyncSession) -> None:
    """Argon2id, **nunca** bcrypt. É convenção que não se negocia, e o prefixo do hash é o que a
    prova — um `$2b$` aqui seria bcrypt entrando por uma troca de biblioteca distraída."""

    user = await make_user(session)

    result = await session.execute(
        sa.select(UserModel.password_hash).where(UserModel.id == user.id)
    )
    password_hash = result.scalars().one()

    assert password_hash is not None
    assert password_hash.startswith("$argon2id$")


async def test_me_sem_cookie_e_401(client: AsyncClient) -> None:
    response = await client.get("/api/me")

    assert response.status_code == 401


async def test_me_com_cookie_devolve_a_identidade(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """`/api/me` é identidade **global**: sem papel, sem organização, sem permissão. Isso muda a
    cada request e é o `access` que resolve, no `orgId` do path."""

    user = await make_user(session, email="bia@widelab.com.br", name="Bia")
    await client.post("/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})

    response = await client.get("/api/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": "bia@widelab.com.br",
        "name": "Bia",
    }


async def test_login_e_case_insensitive_porque_o_email_e_citext(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    """Quem se cadastrou como `Ana@x.com` loga como `ana@x.com`. A comparação é do **banco**
    (CITEXT), não de um `.lower()` na aplicação — e é uma das razões de a suíte falar com
    Postgres de verdade: SQLite não tem CITEXT e este teste passaria verde testando nada."""

    await make_user(session, email="Ana.Maria@Widelab.com.BR")

    response = await client.post(
        "/api/auth/login",
        json={"email": "ana.maria@widelab.com.br", "password": DEFAULT_PASSWORD},
    )

    assert response.status_code == 200


async def test_logout_apaga_o_cookie(client: AsyncClient, session: AsyncSession) -> None:
    user = await make_user(session)
    await client.post("/api/auth/login", json={"email": user.email, "password": DEFAULT_PASSWORD})

    response = await client.post("/api/auth/logout")

    assert response.status_code == 204
    assert (await client.get("/api/me")).status_code == 401
