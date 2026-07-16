"""O que a spec 06 registrou como dívida: o token de uso único, o aceite uniforme, o TTL de 7
dias e a atomicidade do auto-cadastro de Parceiro."""

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
from tests.factories import DEFAULT_PASSWORD, make_company, make_invitation, make_user


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

    from tests.factories import make_partner

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
