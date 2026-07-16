"""O que a spec 04 registrou como dívida: o `CHECK` gerado, a FK composta, `require_permission`,
o alcance do `platform_admin` e o 404 que não é 403."""

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.tenancy import OrganizationType
from src.modules.access.adapters.db.models import Membership as MembershipModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import make_company, make_membership, make_partner, make_user


async def test_o_check_recusa_hr_num_parceiro(session: AsyncSession) -> None:
    """Um `hr` não existe num Parceiro, e **quem garante é o banco**: o `CHECK` de `memberships`
    é gerado a partir de `ROLES_BY_ORGANIZATION_TYPE`, então o mapa do domínio e a tabela não
    podem divergir.

    O `INSERT` aqui é na mão de propósito — a rota daria 422 antes, e o que este teste pergunta é
    o que sobra quando alguém escreve por fora da aplicação."""

    parceiro = await make_partner(session)
    user = await make_user(session)

    with pytest.raises(IntegrityError) as excedeu:
        await session.execute(
            sa.insert(MembershipModel).values(
                user_id=user.id,
                organization_id=parceiro.id,
                organization_type=OrganizationType.PARTNER,
                role=Role.HR,
            )
        )
    await session.rollback()

    assert "ck_memberships_role_matches_organization_type" in str(excedeu.value)


async def test_a_fk_composta_recusa_organization_type_mentido(session: AsyncSession) -> None:
    """**Sem a FK composta, o `CHECK` seria decorativo: bastaria gravar o tipo errado.**

    Repare no cenário: `partner_admin` + `organization_type='partner'` passa no `CHECK` sem
    reclamar — a combinação existe. O que não existe é ela apontando pra uma organização que é
    `company`, e é a FK contra `organizations(id, type)` que descobre isso. Este é o teste que
    prova que as duas garantias são diferentes."""

    empresa = await make_company(session)
    user = await make_user(session)

    with pytest.raises(IntegrityError) as excedeu:
        await session.execute(
            sa.insert(MembershipModel).values(
                user_id=user.id,
                organization_id=empresa.id,
                organization_type=OrganizationType.PARTNER,
                role=Role.PARTNER_ADMIN,
            )
        )
    await session.rollback()

    assert "fk_memberships_organization" in str(excedeu.value)


async def test_require_permission_libera_quem_tem_a_capability(
    session: AsyncSession,
    como: Como,
) -> None:
    """`hr` tem `members.read` — e a rota nomeia a capability, não o papel."""

    acme = await make_company(session, name="Acme")
    rh = await como(role=Role.HR, org=acme)

    response = await rh.get(f"/api/organizacoes/{acme.id}/membros")

    assert response.status_code == 200


async def test_require_permission_nega_quem_nao_tem_a_capability(
    session: AsyncSession,
    como: Como,
) -> None:
    """`finance` alcança a organização (tem vínculo) mas não tem `members.read`. São duas
    negações diferentes compostas no mesmo endpoint: o tenant e a capability."""

    acme = await make_company(session, name="Acme")
    financeiro = await como(role=Role.FINANCE, org=acme)

    response = await financeiro.get(f"/api/organizacoes/{acme.id}/membros")

    assert response.status_code == 403


async def test_platform_admin_alcanca_tenant_onde_nao_tem_vinculo(
    session: AsyncSession,
    como: Como,
) -> None:
    """A Widelab conserta o vínculo de uma Empresa onde ela **não** tem linha em `memberships`.

    E ela se apresenta pelo que é — papel `platform_admin`, persona `platform` — em vez de virar
    um membro fantasma da Empresa."""

    acme = await make_company(session, name="Acme")
    widelab = await como(role=Role.PLATFORM_ADMIN)

    response = await widelab.get(f"/api/organizacoes/{acme.id}/me")

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["role"] == "platform_admin"
    assert corpo["persona"] == "platform"


async def test_patch_de_vinculo_de_outra_organizacao_e_404_e_nao_403(
    session: AsyncSession,
    como: Como,
) -> None:
    """**Contraintuitivo, e é por isso que está aqui: o instinto de quem refatora é "sem acesso é
    403".**

    Quem não pode ver um vínculo também não deveria descobrir que ele existe. O 403 confirmaria o
    id — o 404 não conta nada. Note que quem pede *tem* `members.write` na organização do path: o
    que falta não é permissão, é o vínculo ser dela."""

    acme = await make_company(session, name="Acme")
    globex = await make_company(session, name="Globex")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    pessoa = await make_user(session)
    vinculo_alheio = await make_membership(
        session,
        user_id=pessoa.id,
        organization=globex,
        role=Role.COLLABORATOR,
    )

    response = await admin.patch(
        f"/api/organizacoes/{acme.id}/membros/{vinculo_alheio.id}",
        json={"role": "hr"},
    )

    assert response.status_code == 404


async def test_patch_de_vinculo_inexistente_tambem_e_404(
    session: AsyncSession,
    como: Como,
) -> None:
    """O par do teste acima: os dois casos respondem igual, e é isso que faz o 404 não vazar."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    response = await admin.patch(
        f"/api/organizacoes/{acme.id}/membros/{uuid.uuid4()}",
        json={"role": "hr"},
    )

    assert response.status_code == 404


async def test_a_rota_recusa_papel_que_nao_existe_no_tipo_da_organizacao(
    session: AsyncSession,
    como: Como,
) -> None:
    """A metade educada do `CHECK`: 422 legível, dizendo quais papéis valem. A aplicação explica,
    o banco impede."""

    parceiro = await make_partner(session, name="Bom Prato")
    admin = await como(role=Role.PARTNER_ADMIN, org=parceiro)

    pessoa = await make_user(session)
    vinculo = await make_membership(
        session,
        user_id=pessoa.id,
        organization=parceiro,
        role=Role.PARTNER_OPERATOR,
    )

    response = await admin.patch(
        f"/api/organizacoes/{parceiro.id}/membros/{vinculo.id}",
        json={"role": "hr"},
    )

    assert response.status_code == 422
