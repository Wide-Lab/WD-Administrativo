"""O que a spec 03 registrou como dívida: o 403 do tenant sem vínculo e a integridade dos lados
do convênio.

Dois dos três testes daqui falam SQL direto, sem passar pela rota, e é o ponto: a spec 03 dividiu
o trabalho entre "a aplicação explica" e "o banco impede". Testar só pela rota provaria a
primeira metade e deixaria a segunda — a que sobrevive a um `psql` e a um script de migração —
sem rede nenhuma."""

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.tenancy import OrganizationType
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.adapters.db.models import PartnerAgreement as PartnerAgreementModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import make_agreement, make_company, make_partner


async def test_tenant_sem_vinculo_responde_403(
    session: AsyncSession,
    como: Como,
) -> None:
    """O coração do multi-tenant: o `orgId` viaja no path, e apontar pra organização alheia não
    dá acesso a ela. Sem este 403, a URL seria a autorização."""

    acme = await make_company(session, name="Acme")
    globex = await make_company(session, name="Globex")
    alice = await como(role=Role.COLLABORATOR, org=acme)

    minha = await alice.get(f"/api/organizacoes/{acme.id}")
    alheia = await alice.get(f"/api/organizacoes/{globex.id}")

    assert minha.status_code == 200
    assert alheia.status_code == 403


async def test_organizacao_desativada_nao_abre_nem_para_quem_tem_vinculo(
    session: AsyncSession,
    como: Como,
) -> None:
    """Um tenant desativado não abre — senão "desativado" não significaria nada."""

    from src.modules.access.domain.entities import OrganizationStatus

    acme = await make_company(session, name="Acme", status=OrganizationStatus.DISABLED)
    alice = await como(role=Role.COLLABORATOR, org=acme)

    response = await alice.get(f"/api/organizacoes/{acme.id}")

    assert response.status_code == 403


async def test_o_tipo_de_uma_organizacao_nao_muda_sob_convenio(session: AsyncSession) -> None:
    """`type` é imutável, e a aplicação nem oferece o caminho (`UpdateOrganization` não tem o
    campo). Quem fecha o resto é o banco: a FK composta de `partner_agreements` aponta pra
    `organizations(id, type)`, então trocar o tipo de uma organização conveniada quebra a
    referência do convênio e o Postgres recusa.

    É por isso que o teste faz o `UPDATE` na mão: não existe rota que tente isto. A garantia não
    é "ninguém escreveu o código" — é o banco."""

    empresa = await make_company(session)
    parceiro = await make_partner(session)
    await make_agreement(session, company=empresa, partner=parceiro)

    with pytest.raises(IntegrityError) as excedeu:
        await session.execute(
            sa.update(OrganizationModel)
            .where(OrganizationModel.id == parceiro.id)
            .values(type=OrganizationType.COMPANY)
        )
    await session.rollback()

    assert "fk_partner_agreements_partner" in str(excedeu.value)


async def test_o_banco_recusa_convenio_com_lado_de_tipo_errado(session: AsyncSession) -> None:
    """Uma FK simples pra `organizations(id)` aceitaria qualquer organização dos dois lados. A
    composta contra `organizations(id, type)`, com o tipo fixado em coluna gerada, torna
    impossível pôr uma Empresa no lugar do Parceiro."""

    empresa = await make_company(session)
    outra_empresa = await make_company(session)

    with pytest.raises(IntegrityError) as excedeu:
        await session.execute(
            sa.insert(PartnerAgreementModel).values(
                company_id=empresa.id,
                partner_id=outra_empresa.id,
            )
        )
    await session.rollback()

    assert "fk_partner_agreements_partner" in str(excedeu.value)


async def test_a_rota_recusa_convenio_com_lado_de_tipo_errado(
    session: AsyncSession,
    como: Como,
) -> None:
    """A metade educada da mesma regra: 422 legível antes de o banco precisar falar."""

    acme = await make_company(session, name="Acme")
    globex = await make_company(session, name="Globex")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    response = await admin.post(
        f"/api/organizacoes/{acme.id}/convenios",
        json={"partner_id": str(globex.id)},
    )

    assert response.status_code == 422


async def test_convenio_entre_empresa_e_parceiro_nasce_ativo(
    session: AsyncSession,
    como: Como,
) -> None:
    acme = await make_company(session, name="Acme")
    bom_prato = await make_partner(session, name="Bom Prato")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    response = await admin.post(
        f"/api/organizacoes/{acme.id}/convenios",
        json={"partner_id": str(bom_prato.id)},
    )

    assert response.status_code == 201
    corpo = response.json()
    assert corpo["company_id"] == str(acme.id)
    assert corpo["partner_id"] == str(bom_prato.id)
    assert corpo["status"] == "active"


async def test_so_existe_uma_organizacao_platform(session: AsyncSession) -> None:
    """A Widelab como operadora é singleton, e quem garante é o índice único parcial do banco —
    `company` e `partner` seguem sem limite."""

    with pytest.raises(IntegrityError) as excedeu:
        await session.execute(
            sa.insert(OrganizationModel).values(
                type=OrganizationType.PLATFORM,
                name="Uma Segunda Plataforma",
            )
        )
    await session.rollback()

    assert "uq_organizations_single_platform" in str(excedeu.value)


async def test_rota_de_tenant_sem_sessao_e_401(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    acme = await make_company(session)

    response = await client.get(f"/api/organizacoes/{acme.id}")

    assert response.status_code == 401
