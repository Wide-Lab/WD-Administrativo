"""O que a spec 06 registrou como dívida: o token de uso único, o aceite uniforme, o TTL de 7
dias e a atomicidade do auto-cadastro de Parceiro.

A partir da spec 08, também a **gestão**: listar com status efetivo, revogar por `UPDATE`
condicional, e o `partner_admin` que finalmente faz um Parceiro crescer."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_config
from src.modules.access.adapters.db.models import Invitation as InvitationModel
from src.modules.access.adapters.db.models import Membership as MembershipModel
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import InvitationStatus, Role
from src.modules.auth.adapters.db.models import User as UserModel
from tests.conftest import Como
from tests.factories import (
    DEFAULT_PASSWORD,
    make_company,
    make_invitation,
    make_partner,
    make_user,
)


async def test_o_token_de_convite_e_de_uso_unico(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """**O token é credencial, e credencial que serve duas vezes não é de uso único.**

    O aceite gasta o token por um `UPDATE` condicional, e não por um `if`: é isso que impede que
    dois aceites do mesmo token criem dois vínculos. Reaceitar responde 410 sem abrir sessão."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
    )

    primeiro = await client.post(
        f"/api/convites/{convite.token}/aceitar",
        json={"password": DEFAULT_PASSWORD},
    )
    segundo = await client.post(
        f"/api/convites/{convite.token}/aceitar",
        json={"password": DEFAULT_PASSWORD},
    )

    assert primeiro.status_code == 200
    assert segundo.status_code == 410

    vinculos = await session.execute(
        sa.select(sa.func.count())
        .select_from(MembershipModel)
        .where(MembershipModel.organization_id == acme.id)
    )
    assert vinculos.scalars().one() == 1


async def test_o_aceite_cria_login_vinculo_e_sessao(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Aceitar **é** entrar: cria o login se não houver, cria o vínculo com o papel prometido e
    já emite sessão. O convite carrega o papel; o vínculo só nasce aqui."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.HR,
        invited_by=quem_convidou.id,
        email="nova@widelab.com.br",
    )

    response = await client.post(
        f"/api/convites/{convite.token}/aceitar",
        json={"password": DEFAULT_PASSWORD, "name": "Nova Pessoa"},
    )

    assert response.status_code == 200
    assert get_config().SESSION_COOKIE_NAME in response.cookies

    eu = await client.get("/api/me")
    assert eu.json()["email"] == "nova@widelab.com.br"
    assert eu.json()["name"] == "Nova Pessoa"

    meu_papel = await client.get(f"/api/organizacoes/{acme.id}/me")
    assert meu_papel.json()["role"] == "hr"


async def test_o_aceite_responde_igual_para_quem_ja_tem_conta_e_para_quem_nao_tem(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """**A resposta não pode virar um oráculo de quem já é cadastrado.**

    E repare no segundo `assert`: a senha de quem já tinha conta **não** é trocada. É o que
    impede o convite de virar um caminho de redefinição de senha alheia — bastaria convidar um
    e-mail existente. Os dois caminhos respondem igual justamente porque um deles ignora a senha
    do corpo."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)

    ja_tem_conta = await make_user(session, email="ana@widelab.com.br")
    convite_de_quem_tem = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="ana@widelab.com.br",
    )
    convite_de_quem_nao_tem = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="bia@widelab.com.br",
    )

    hash_antes = (
        (
            await session.execute(
                sa.select(UserModel.password_hash).where(UserModel.id == ja_tem_conta.id)
            )
        )
        .scalars()
        .one()
    )

    de_quem_tem = await client.post(
        f"/api/convites/{convite_de_quem_tem.token}/aceitar",
        json={"password": "outra-senha-qualquer-123"},
    )
    de_quem_nao_tem = await client.post(
        f"/api/convites/{convite_de_quem_nao_tem.token}/aceitar",
        json={"password": "outra-senha-qualquer-123"},
    )

    assert de_quem_tem.status_code == de_quem_nao_tem.status_code == 200
    assert de_quem_tem.text == de_quem_nao_tem.text

    hash_depois = (
        (
            await session.execute(
                sa.select(UserModel.password_hash).where(UserModel.id == ja_tem_conta.id)
            )
        )
        .scalars()
        .one()
    )
    assert hash_depois == hash_antes


async def test_convite_vencido_responde_410_sem_gravar_expired(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """**`status = 'expired'` nunca é gravado, e isso é decisão.**

    Quem sabe se um convite venceu é `expires_at` comparado com o agora. Gravar o status exigiria
    um cron pra manter a coluna honesta, e até ele rodar um convite vencido responderia
    `pending` — duas fontes da verdade divergindo justamente no instante que importa."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    consulta = await client.get(f"/api/convites/{convite.token}")
    aceite = await client.post(
        f"/api/convites/{convite.token}/aceitar",
        json={"password": DEFAULT_PASSWORD},
    )

    assert consulta.status_code == 410
    assert aceite.status_code == 410

    await session.refresh(convite)
    assert convite.status is InvitationStatus.PENDING


async def test_o_convite_criado_pela_rota_vence_em_sete_dias(
    session: AsyncSession,
    como: Como,
) -> None:
    """O TTL de 7 dias da spec 06, vindo do `INVITATION_TTL_DAYS` da config."""

    acme = await make_company(session, name="Acme")
    rh = await como(role=Role.HR, org=acme)

    response = await rh.post(
        f"/api/organizacoes/{acme.id}/convites",
        json={"email": "nova@widelab.com.br", "role": "collaborator"},
    )

    assert response.status_code == 201
    expira_em = datetime.fromisoformat(response.json()["expires_at"]) - datetime.now(UTC)
    assert timedelta(days=6, hours=23) < expira_em <= timedelta(days=7)


async def test_o_convite_nao_devolve_o_token_para_quem_convidou(
    session: AsyncSession,
    como: Como,
) -> None:
    """O token é credencial e sai por e-mail, pro convidado. Devolvê-lo aqui deixaria qualquer
    `hr` aceitar o convite que emitiu no lugar da pessoa — e o e-mail deixaria de ser a prova de
    que quem aceitou controla a caixa."""

    acme = await make_company(session, name="Acme")
    rh = await como(role=Role.HR, org=acme)

    response = await rh.post(
        f"/api/organizacoes/{acme.id}/convites",
        json={"email": "nova@widelab.com.br", "role": "collaborator"},
    )

    assert "token" not in response.json()


async def test_convite_para_organizacao_alheia_e_403(
    session: AsyncSession,
    como: Como,
) -> None:
    """Um `hr` só convida pra **sua** organização: a permissão é resolvida no `orgId` do path, e
    o papel dele na própria Empresa não viaja pra fora dela. Sem `if` na rota."""

    acme = await make_company(session, name="Acme")
    globex = await make_company(session, name="Globex")
    rh_da_acme = await como(role=Role.HR, org=acme)

    response = await rh_da_acme.post(
        f"/api/organizacoes/{globex.id}/convites",
        json={"email": "nova@widelab.com.br", "role": "collaborator"},
    )

    assert response.status_code == 403


async def test_token_que_nunca_existiu_e_404(client: AsyncClient) -> None:
    """404 pro que nunca existiu, 410 pro que existiu e não vale mais — são perguntas
    diferentes."""

    response = await client.get("/api/convites/token-que-nunca-existiu")

    assert response.status_code == 404


async def test_auto_cadastro_de_parceiro_cria_organizacao_admin_e_vinculo(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """A rota **pública** que cria organização sem `platform_admin` — o Parceiro é organização de
    primeiro nível. Isso não lhe dá acesso a Empresa nenhuma: quem o liga a cada uma é o
    convênio."""

    response = await client.post(
        "/api/parceiros/cadastro",
        json={
            "company_name": "Bom Prato",
            "document": "12345678000199",
            "admin": {
                "name": "Dona do Bom Prato",
                "email": "dono@bomprato.com.br",
                "password": DEFAULT_PASSWORD,
            },
        },
    )

    assert response.status_code == 201
    assert get_config().SESSION_COOKIE_NAME in response.cookies

    contexto = await client.get("/api/me/contexto")
    vinculos = contexto.json()["memberships"]
    assert len(vinculos) == 1
    assert vinculos[0]["role"] == "partner_admin"
    assert vinculos[0]["organization"]["type"] == "partner"
    assert vinculos[0]["organization"]["name"] == "Bom Prato"


async def test_auto_cadastro_com_email_ja_cadastrado_responde_409(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """O caso comum, que o use case pega antes de escrever qualquer coisa."""

    await make_user(session, email="dono@bomprato.com.br")

    response = await client.post(
        "/api/parceiros/cadastro",
        json={
            "company_name": "Bom Prato",
            "admin": {
                "name": "Dona do Bom Prato",
                "email": "dono@bomprato.com.br",
                "password": DEFAULT_PASSWORD,
            },
        },
    )

    assert response.status_code == 409


async def test_auto_cadastro_que_falha_no_meio_nao_deixa_organizacao_orfa(
    session: AsyncSession,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**O teste caro da spec 06, e a razão de o harness usar `TRUNCATE` em vez de rollback.**

    O use case confere o e-mail *antes* de criar a organização, então o caminho comum nunca chega
    a escrever — e um teste que só mandasse e-mail duplicado passaria verde sem tocar na
    transação. O `monkeypatch` abaixo apaga **só** essa conferência prévia, reproduzindo a corrida
    que o docstring do use case descreve: dois cadastros simultâneos em que o segundo passa pelo
    `find_id_by_email` e só descobre a colisão no `INSERT`.

    Aí a pergunta que importa fica de pé: a organização já foi inserida quando o `users` estoura.
    O que a desfaz não é um `try` — é `organizations` e `users` compartilharem a sessão da
    requisição, com um `commit` só cobrindo as duas. Se alguém der uma uow própria ao
    `UserDirectory`, este teste cai, e é pra isso que ele existe."""

    from src.modules.auth.adapters.db.user_directory import SqlAlchemyUserDirectory

    await make_user(session, email="dono@bomprato.com.br")

    async def _finge_que_o_email_esta_livre(
        self: SqlAlchemyUserDirectory,
        email: str,
    ) -> None:
        return None

    monkeypatch.setattr(
        SqlAlchemyUserDirectory,
        "find_id_by_email",
        _finge_que_o_email_esta_livre,
    )

    response = await client.post(
        "/api/parceiros/cadastro",
        json={
            "company_name": "Parceiro Órfão",
            "admin": {
                "name": "Dona do Bom Prato",
                "email": "dono@bomprato.com.br",
                "password": DEFAULT_PASSWORD,
            },
        },
    )

    assert response.status_code == 409

    orfas = await session.execute(
        sa.select(sa.func.count())
        .select_from(OrganizationModel)
        .where(OrganizationModel.name == "Parceiro Órfão")
    )
    assert orfas.scalars().one() == 0


async def test_convite_para_papel_que_nao_existe_no_tipo_da_organizacao_e_422(
    session: AsyncSession,
    como: Como,
) -> None:
    """A mesma regra de `memberships` vale no convite, porque o convite carrega o papel. Sem ela,
    o convite nasceria e só falharia no aceite — o erro apareceria na cara do convidado, não na de
    quem convidou errado."""

    acme = await make_company(session, name="Acme")
    rh = await como(role=Role.HR, org=acme)

    response = await rh.post(
        f"/api/organizacoes/{acme.id}/convites",
        json={"email": "nova@widelab.com.br", "role": "partner_admin"},
    )

    assert response.status_code == 422


async def test_a_tela_publica_de_aceite_ve_o_convite_sem_sessao(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Rota pública: quem vai aceitar ainda não tem sessão — o que autoriza é o token. E ela
    devolve o mínimo: nada de ids internos, porque quem não aceitou não é membro de nada."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="nova@widelab.com.br",
    )

    response = await client.get(f"/api/convites/{convite.token}")

    assert response.status_code == 200
    assert response.json() == {
        "organization_name": "Acme",
        "email": "nova@widelab.com.br",
        "role": "collaborator",
        "expires_at": response.json()["expires_at"],
    }


async def test_o_banco_recusa_convite_de_hr_para_parceiro(session: AsyncSession) -> None:
    """O `CHECK` de `invitations` é o mesmo de `memberships`, gerado da mesma função — e não é
    coincidência: um convite é um vínculo que ainda não aconteceu."""

    parceiro = await make_partner(session)
    quem_convidou = await make_user(session)

    with pytest.raises(sa.exc.IntegrityError) as excedeu:
        await session.execute(
            sa.insert(InvitationModel).values(
                email="nova@widelab.com.br",
                organization_id=parceiro.id,
                organization_type=parceiro.type,
                role=Role.HR,
                token="um-token-qualquer",
                expires_at=datetime.now(UTC) + timedelta(days=7),
                invited_by=quem_convidou.id,
            )
        )
    await session.rollback()

    assert "ck_invitations_role_matches_organization_type" in str(excedeu.value)


# --------------------------------------------------------------------------------------------
# Spec 08 — gestão de convites: listar, revogar, e o Parceiro que cresce.
# --------------------------------------------------------------------------------------------


async def test_a_listagem_devolve_os_pendentes_da_organizacao_sem_token(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 1. **Escopada pelo `orgId` do path, e sem o token em item nenhum.**

    O escopo não é cortesia: sem o filtro por organização, um `hr` da Acme leria a fila de
    contratação da Globex. E o token seguir fora vale tanto aqui quanto no `POST` — uma listagem
    que o devolvesse desfaria de uma vez o cuidado que a spec 06 teve no create."""

    acme = await make_company(session, name="Acme")
    globex = await make_company(session, name="Globex")
    quem_convidou = await make_user(session)

    meu = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="nossa@widelab.com.br",
    )
    da_outra = await make_invitation(
        session,
        organization=globex,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="alheia@widelab.com.br",
    )

    rh = await como(role=Role.HR, org=acme)
    response = await rh.get(f"/api/organizacoes/{acme.id}/convites")

    assert response.status_code == 200

    corpo = response.json()
    assert corpo["total"] == 1
    assert corpo["page"] == 1
    assert [item["id"] for item in corpo["items"]] == [str(meu.id)]
    assert str(da_outra.id) not in response.text
    assert all("token" not in item for item in corpo["items"])


async def test_a_listagem_mostra_expired_sem_que_nada_tenha_gravado_a_coluna(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 2. **A expiração é derivada, e a listagem lê a mesma verdade que o aceite.**

    Um convite vencido tem `status = 'pending'` no banco — `expired` nunca é gravado (spec 06).
    Se a listagem copiasse a coluna, a tela de gestão mostraria como "aguardando" um convite que
    o aceite já recusa com 410: duas telas do mesmo produto discordando sobre o mesmo convite."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    vencido = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    rh = await como(role=Role.HR, org=acme)
    response = await rh.get(f"/api/organizacoes/{acme.id}/convites?status=expired")

    assert response.status_code == 200
    assert [item["status"] for item in response.json()["items"]] == ["expired"]

    await session.refresh(vencido)
    assert vencido.status is InvitationStatus.PENDING


async def test_o_filtro_de_status_responde_pelo_efetivo_e_o_default_e_pending(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 3, e o teste que **segura as duas escritas da mesma regra juntas**.

    O status efetivo é escrito duas vezes: em `Invitation.effective_status` (Python, item a
    item) e em `_effective_status_condition` (SQL, no `WHERE` que a paginação conta). Elas podem
    divergir em silêncio, e este teste é o que não deixa — cada item volta com o `status` que a
    **entidade** derivou, então filtrar por `X` e receber um item que diz `Y` acusa a divergência
    na hora.

    O default ser `pending`, e não "tudo", é a outra metade: a pergunta que a tela faz primeiro é
    o que ainda está de pé pra alguém aceitar."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)

    esperados = {
        "pending": await make_invitation(
            session,
            organization=acme,
            role=Role.COLLABORATOR,
            invited_by=quem_convidou.id,
        ),
        "expired": await make_invitation(
            session,
            organization=acme,
            role=Role.COLLABORATOR,
            invited_by=quem_convidou.id,
            expires_at=datetime.now(UTC) - timedelta(days=1),
        ),
        "accepted": await make_invitation(
            session,
            organization=acme,
            role=Role.COLLABORATOR,
            invited_by=quem_convidou.id,
            status=InvitationStatus.ACCEPTED,
        ),
        "revoked": await make_invitation(
            session,
            organization=acme,
            role=Role.COLLABORATOR,
            invited_by=quem_convidou.id,
            status=InvitationStatus.REVOKED,
        ),
    }

    rh = await como(role=Role.HR, org=acme)

    for status_pedido, convite in esperados.items():
        response = await rh.get(f"/api/organizacoes/{acme.id}/convites?status={status_pedido}")

        assert response.status_code == 200, response.text
        itens = response.json()["items"]
        assert [item["id"] for item in itens] == [str(convite.id)], status_pedido
        # A agulha: o status que a entidade derivou é o que o filtro do SQL prometeu.
        assert [item["status"] for item in itens] == [status_pedido]

    sem_filtro = await rh.get(f"/api/organizacoes/{acme.id}/convites")
    assert [item["id"] for item in sem_filtro.json()["items"]] == [str(esperados["pending"].id)]


async def test_revogar_fecha_o_ciclo_que_a_06_so_fechava_por_psql(
    session: AsyncSession,
    client: AsyncClient,
    como: Como,
) -> None:
    """Critério 4. **O buraco da spec 06, agora tapado pela API.**

    Revogar era um `UPDATE` no `psql`; o que este teste cobra é o ciclo inteiro pela rota — o
    204, a coluna gravada, e as duas pontas públicas passando a recusar com 410. O `assert` do
    vínculo é o que impede o teste de passar com uma revogação que revoga só de mentira."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="nunca@widelab.com.br",
    )

    rh = await como(role=Role.HR, org=acme)
    revogacao = await rh.delete(f"/api/organizacoes/{acme.id}/convites/{convite.id}")

    assert revogacao.status_code == 204
    assert revogacao.content == b""

    await session.refresh(convite)
    assert convite.status is InvitationStatus.REVOKED

    consulta = await client.get(f"/api/convites/{convite.token}")
    aceite = await client.post(
        f"/api/convites/{convite.token}/aceitar",
        json={"password": DEFAULT_PASSWORD},
    )

    assert consulta.status_code == 410
    assert aceite.status_code == 410

    vinculos = await session.execute(
        sa.select(sa.func.count())
        .select_from(MembershipModel)
        .where(MembershipModel.organization_id == acme.id)
    )
    # Só o do próprio `hr`, criado pela fixture — o convidado não entrou.
    assert vinculos.scalars().one() == 1


async def test_revogar_convite_aceito_e_409_e_o_vinculo_continua_de_pe(
    session: AsyncSession,
    client: AsyncClient,
    como: Como,
) -> None:
    """Critério 5, primeira metade. **O 409 é o que separa esta rota de um `DELETE` idempotente
    puro.**

    Um convite aceito virou membro. Responder 204 aqui seria dizer "revoguei" a quem queria tirar
    o acesso de alguém — e o acesso continuaria lá, porque quem o dá é o `membership`, não o
    convite. O 409 manda a pessoa pro `PATCH .../membros/{id}`, que é `members.write`."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="entrou@widelab.com.br",
    )

    aceite = await client.post(
        f"/api/convites/{convite.token}/aceitar",
        json={"password": DEFAULT_PASSWORD},
    )
    assert aceite.status_code == 200

    rh = await como(role=Role.HR, org=acme)
    response = await rh.delete(f"/api/organizacoes/{acme.id}/convites/{convite.id}")

    assert response.status_code == 409

    await session.refresh(convite)
    assert convite.status is InvitationStatus.ACCEPTED

    entrou = await session.execute(
        sa.select(sa.func.count())
        .select_from(MembershipModel)
        .join(UserModel, MembershipModel.user_id == UserModel.id)
        .where(
            MembershipModel.organization_id == acme.id,
            UserModel.email == "entrou@widelab.com.br",
        )
    )
    assert entrou.scalars().one() == 1


async def test_revogar_duas_vezes_e_204_nas_duas(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 5, segunda metade. O `DELETE` afirma um estado, e afirmá-lo de novo não é erro —
    o convite já está revogado, que é o que quem chamou queria."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
    )

    rh = await como(role=Role.HR, org=acme)
    primeira = await rh.delete(f"/api/organizacoes/{acme.id}/convites/{convite.id}")
    segunda = await rh.delete(f"/api/organizacoes/{acme.id}/convites/{convite.id}")

    assert primeira.status_code == segunda.status_code == 204


async def test_convite_de_outra_organizacao_e_404_e_nao_403(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 6. **404, não 403 — a resposta não pode virar oráculo.**

    Um 403 aqui confirmaria que o convite existe: bastaria varrer ids pra descobrir o que a
    concorrente está contratando. Mesma escolha do `PATCH .../membros/{id}` da spec 04. O
    `assert` do id inexistente é o par que dá sentido ao primeiro — as duas perguntas têm que ser
    **indistinguíveis** de fora."""

    acme = await make_company(session, name="Acme")
    globex = await make_company(session, name="Globex")
    quem_convidou = await make_user(session)
    da_globex = await make_invitation(
        session,
        organization=globex,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
    )

    rh_da_acme = await como(role=Role.HR, org=acme)

    alheio = await rh_da_acme.delete(f"/api/organizacoes/{acme.id}/convites/{da_globex.id}")
    inexistente = await rh_da_acme.delete(f"/api/organizacoes/{acme.id}/convites/{uuid.uuid4()}")
    listagem = await rh_da_acme.get(f"/api/organizacoes/{acme.id}/convites")

    assert alheio.status_code == 404
    assert inexistente.status_code == 404
    assert alheio.json() == inexistente.json()
    assert listagem.json()["total"] == 0

    # E o convite da Globex segue intacto: o 404 não foi um 204 disfarçado.
    await session.refresh(da_globex)
    assert da_globex.status is InvitationStatus.PENDING


async def test_gestao_de_convite_sem_sessao_e_401(
    session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Critério 6, segunda metade. As rotas de gestão são o oposto das públicas de aceite: lá o
    token autoriza, aqui é a sessão."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
    )

    listagem = await client.get(f"/api/organizacoes/{acme.id}/convites")
    revogacao = await client.delete(f"/api/organizacoes/{acme.id}/convites/{convite.id}")

    assert listagem.status_code == 401
    assert revogacao.status_code == 401


@pytest.mark.parametrize("role", [Role.FINANCE, Role.COLLABORATOR, Role.MANAGER])
async def test_papel_sem_invitations_read_nao_lista_convites(
    session: AsyncSession,
    como: Como,
    role: Role,
) -> None:
    """Critério 7. Quem convida enxerga o que convidou; ninguém a mais — a fila de contratação
    conta quem está entrando, e não é leitura de todo mundo da Empresa."""

    acme = await make_company(session, name="Acme")
    quem_nao_pode = await como(role=role, org=acme)

    response = await quem_nao_pode.get(f"/api/organizacoes/{acme.id}/convites")

    assert response.status_code == 403


async def test_partner_operator_nao_lista_convites_do_seu_parceiro(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 7, no lado do Parceiro. O `partner_admin` recebeu as duas capabilities; o
    operador, nenhuma — e o par positivo é `test_partner_admin_convida_e_o_parceiro_cresce`."""

    bom_prato = await make_partner(session, name="Bom Prato")
    operador = await como(role=Role.PARTNER_OPERATOR, org=bom_prato)

    response = await operador.get(f"/api/organizacoes/{bom_prato.id}/convites")

    assert response.status_code == 403


async def test_papel_sem_invitations_write_nao_revoga(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 7, segunda metade — e o par positivo mora nos testes de revogação acima, que é o
    que faz este 403 significar "faltou permissão" e não "a rota não funciona"."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
    )

    colaborador = await como(role=Role.COLLABORATOR, org=acme)
    response = await colaborador.delete(f"/api/organizacoes/{acme.id}/convites/{convite.id}")

    assert response.status_code == 403

    await session.refresh(convite)
    assert convite.status is InvitationStatus.PENDING


async def test_platform_admin_nao_convida_nem_le_convite_do_cliente(
    session: AsyncSession,
    como: Como,
) -> None:
    """Contraintuitivo, e é o ponto — o instinto de quem refatora é "admin pode tudo".

    Convidar é ato da organização, não da Plataforma: a Widelab provisiona tenant e conserta
    vínculo pela CLI, mas não chama gente pro time do cliente nem lê a fila de contratação dele.
    Mesma decisão do `agreements.write` (spec 04). E note de onde vem o 403: o
    `require_permission` **afrouxa** pra `platform_admin`, somando as permissões de plataforma em
    qualquer `orgId` — então ele é negado por o mapa não lhe dar `invitations.*`, e não por não
    alcançar a Acme."""

    acme = await make_company(session, name="Acme")
    da_widelab = await como(role=Role.PLATFORM_ADMIN)

    listagem = await da_widelab.get(f"/api/organizacoes/{acme.id}/convites")
    convite = await da_widelab.post(
        f"/api/organizacoes/{acme.id}/convites",
        json={"email": "nova@widelab.com.br", "role": "collaborator"},
    )

    assert listagem.status_code == 403
    assert convite.status_code == 403


async def test_partner_admin_convida_e_o_parceiro_cresce(
    session: AsyncSession,
    client: AsyncClient,
    como: Como,
) -> None:
    """Critério 8. **O buraco do crescimento, fechado sem rota nova.**

    Como o auto-cadastro (spec 06) cria só o primeiro `partner_admin`, o segundo membro de um
    Parceiro só nascia pela CLI. Agora nasce pelas **mesmas** três rotas de convite — o que mudou
    foi uma linha num `frozenset`, e é isso que este teste prova ponta a ponta: convite, aceite,
    vínculo com papel de Parceiro, persona resolvida."""

    bom_prato = await make_partner(session, name="Bom Prato")
    dono = await como(role=Role.PARTNER_ADMIN, org=bom_prato)

    convite = await dono.post(
        f"/api/organizacoes/{bom_prato.id}/convites",
        json={"email": "operador@bomprato.com.br", "role": "partner_operator"},
    )
    assert convite.status_code == 201, convite.text

    listagem = await dono.get(f"/api/organizacoes/{bom_prato.id}/convites")
    assert listagem.status_code == 200
    assert listagem.json()["total"] == 1

    # O token não sai por nenhuma rota de gestão — quem o tem é o e-mail do convidado. Aqui ele
    # vem do banco justamente porque a API não o entrega, que é o ponto da spec 06.
    token = (
        (
            await session.execute(
                sa.select(InvitationModel.token).where(
                    InvitationModel.id == uuid.UUID(convite.json()["id"])
                )
            )
        )
        .scalars()
        .one()
    )

    aceite = await client.post(
        f"/api/convites/{token}/aceitar",
        json={"password": DEFAULT_PASSWORD, "name": "Operador do Bom Prato"},
    )
    assert aceite.status_code == 200

    meu_papel = await client.get(f"/api/organizacoes/{bom_prato.id}/me")
    assert meu_papel.json()["role"] == "partner_operator"
    assert meu_papel.json()["persona"] == "partner"


async def test_partner_admin_nao_convida_papel_de_empresa(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 8, segunda parte. O 422 é a aplicação explicando; quem **impede** é o `CHECK`
    gerado do banco, e isso tem teste próprio (`test_o_banco_recusa_convite_de_hr_para_parceiro`)
    — a mesma divisão de trabalho da spec 06: a aplicação explica, o banco impede."""

    bom_prato = await make_partner(session, name="Bom Prato")
    dono = await como(role=Role.PARTNER_ADMIN, org=bom_prato)

    response = await dono.post(
        f"/api/organizacoes/{bom_prato.id}/convites",
        json={"email": "rh@bomprato.com.br", "role": "hr"},
    )

    assert response.status_code == 422


async def test_partner_operator_nao_convida(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 8, terceira parte. Parceiro cresce pela mão do **seu admin**, como a Empresa —
    dar `invitations.write` a todo mundo do Parceiro faria o convite deixar de ser decisão."""

    bom_prato = await make_partner(session, name="Bom Prato")
    operador = await como(role=Role.PARTNER_OPERATOR, org=bom_prato)

    response = await operador.post(
        f"/api/organizacoes/{bom_prato.id}/convites",
        json={"email": "outro@bomprato.com.br", "role": "partner_operator"},
    )

    assert response.status_code == 403


async def test_dois_delete_simultaneos_nao_corrompem_o_convite(
    session: AsyncSession,
    como: Como,
) -> None:
    """Critério 9, primeira metade. Os dois respondem 204 e o convite acaba revogado uma vez só —
    o banco decide quem chegou primeiro, e o segundo é um no-op sobre `revoked`."""

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
    )

    rh = await como(role=Role.HR, org=acme)
    rota = f"/api/organizacoes/{acme.id}/convites/{convite.id}"

    primeira, segunda = await asyncio.gather(rh.delete(rota), rh.delete(rota))

    assert primeira.status_code == 204
    assert segunda.status_code == 204

    await session.refresh(convite)
    assert convite.status is InvitationStatus.REVOKED


async def test_a_revogacao_e_guardada_pelo_banco_e_nao_por_uma_leitura(
    session: AsyncSession,
    client: AsyncClient,
    como: Como,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Critério 9, segunda metade — **o teste que prende a forma, e não só o resultado.**

    "É um `UPDATE ... WHERE status = 'pending'`, não uma leitura seguida de escrita" é a parte da
    spec que uma refatoração inocente desfaz sem quebrar nenhum dos testes acima: trocar por
    `if convite.status is PENDING: update(...)` passa em todos eles e reintroduz a corrida.

    Então aqui a leitura **mente**. `get_by_id_or_none` é substituída por uma que jura que o
    convite está `pending`, enquanto o banco o tem como `accepted`. Numa implementação que decide
    pela leitura, essa mentira vira escrita: o `accepted` seria sobrescrito por `revoked`, e o
    vínculo do convidado ficaria órfão de convite. Na implementação real a escrita condicional já
    aconteceu — e não afetou linha nenhuma — **antes** de alguém ler, então a mentira não tem o
    que estragar.

    A pergunta é o **efeito no banco**, não o código de resposta: sob uma leitura mentirosa o
    status HTTP é artefato do teste; a coluna é o produto."""

    from dataclasses import replace

    from src.modules.access.adapters.db.repository import InvitationRepository
    from src.modules.access.domain.entities import Invitation

    acme = await make_company(session, name="Acme")
    quem_convidou = await make_user(session)
    convite = await make_invitation(
        session,
        organization=acme,
        role=Role.COLLABORATOR,
        invited_by=quem_convidou.id,
        email="entrou@widelab.com.br",
    )

    aceite = await client.post(
        f"/api/convites/{convite.token}/aceitar",
        json={"password": DEFAULT_PASSWORD},
    )
    assert aceite.status_code == 200

    await session.refresh(convite)
    mentira = replace(
        InvitationRepository(session)._to_entity(convite),
        status=InvitationStatus.PENDING,
    )

    async def _jura_que_esta_pendente(
        self: InvitationRepository,
        id_: uuid.UUID,
    ) -> Invitation:
        return mentira

    monkeypatch.setattr(InvitationRepository, "get_by_id_or_none", _jura_que_esta_pendente)

    rh = await como(role=Role.HR, org=acme)
    await rh.delete(f"/api/organizacoes/{acme.id}/convites/{convite.id}")

    await session.refresh(convite)
    assert convite.status is InvitationStatus.ACCEPTED
