"""O que a spec 05 registrou como dívida: a negação por padrão, o `platform_admin` que **não**
afrouxa, e os `modules` do `/me`.

**Sobre a rota de prova:** `refeicoes` e `frota` são hoje só chaves registradas — descritores sem
`router`, até as fases 2 e 3. Ou seja, não existe no app um único endpoint atrás do
`require_module`, e sem inventar um não haveria como perguntar a ele 200 ou 403. A fixture
`rota_de_prova` pendura um endpoint mínimo atrás do guard **de verdade**, com a chave real
`refeicoes`, e some quando o primeiro app de negócio existir. Ver `Como ficou` da spec 07."""

from collections.abc import AsyncIterator

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import ModuleEntitlement as ModuleEntitlementModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import make_company, make_entitlement, make_partner, make_user


@pytest.fixture(scope="session")
async def rota_de_prova(database_url: str) -> AsyncIterator[str]:
    """Um endpoint atrás do `require_module("refeicoes")` — o que a fase 2 vai trazer de verdade.

    Não passa por `mount_module` e não registra módulo nenhum de propósito: mexer no
    `ModuleRegistry`, que é global e vive pelo processo inteiro, vazaria pro catálogo do
    `GET /modulos` de outros testes. O que se quer aqui é o guard, e o guard só consulta o
    entitlement."""

    from fastapi import APIRouter, Depends

    from src.api.modules import REFEICOES
    from src.core.modules import require_module
    from src.main import app

    router = APIRouter()

    @router.get(
        f"/organizacoes/{{orgId}}/{REFEICOES.key}/prova",
        dependencies=[Depends(require_module(REFEICOES.key))],
    )
    async def prova() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router, prefix="/api")

    yield "/api/organizacoes/{org_id}/" + REFEICOES.key + "/prova"


async def test_require_module_nega_por_padrao(
    session: AsyncSession,
    como: Como,
    rota_de_prova: str,
) -> None:
    """**Ausência de linha em `module_entitlements` é o "não".** Um tenant recém-criado tem tudo
    negado sem ninguém escrever nada — e quem pede aqui é o `company_admin` da própria Empresa,
    pra o 403 não poder ser confundido com falta de papel."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    response = await admin.get(rota_de_prova.format(org_id=acme.id))

    assert response.status_code == 403


async def test_require_module_libera_quando_a_empresa_contratou(
    session: AsyncSession,
    como: Como,
    rota_de_prova: str,
) -> None:
    """O par do teste acima: sem ele, o 403 poderia estar vindo de qualquer outra coisa.

    Vender é ligar o flag — uma linha, sem deploy."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)
    widelab = await make_user(session)
    await make_entitlement(
        session,
        organization=acme,
        module_key="refeicoes",
        granted_by=widelab.id,
    )

    response = await admin.get(rota_de_prova.format(org_id=acme.id))

    assert response.status_code == 200


async def test_require_module_nao_afrouxa_nem_para_platform_admin(
    session: AsyncSession,
    como: Como,
    rota_de_prova: str,
) -> None:
    """**Contraintuitivo, e é exatamente por isso que está aqui: o instinto de quem refatora é
    "admin pode tudo".**

    `require_permission` afrouxa pra `platform_admin`; este guard não afrouxa pra ninguém, porque
    a pergunta é outra — não "quem é você", e sim "o que o *tenant* comprou". Um módulo que a
    Empresa não contratou não abre nem pra Widelab: entitlement é fato comercial, não privilégio.

    Note que o `platform_admin` **alcança** a Acme (o `current_organization` deixou passar): o 403
    vem do entitlement, não do tenant."""

    acme = await make_company(session, name="Acme")
    widelab = await como(role=Role.PLATFORM_ADMIN)

    alcanca_o_tenant = await widelab.get(f"/api/organizacoes/{acme.id}/me")
    response = await widelab.get(rota_de_prova.format(org_id=acme.id))

    assert alcanca_o_tenant.status_code == 200
    assert response.status_code == 403


async def test_require_module_nega_num_parceiro(
    session: AsyncSession,
    como: Como,
    rota_de_prova: str,
) -> None:
    """Só Empresa contrata módulo. Como o Parceiro alcança o módulo da Empresa que ele atende
    (pelo convênio) é decisão do primeiro app de negócio, na fase 2."""

    bom_prato = await make_partner(session, name="Bom Prato")
    admin = await como(role=Role.PARTNER_ADMIN, org=bom_prato)

    response = await admin.get(rota_de_prova.format(org_id=bom_prato.id))

    assert response.status_code == 403


async def test_me_devolve_os_modulos_habilitados_do_tenant(
    session: AsyncSession,
    como: Como,
) -> None:
    """`modules` é da **organização**, não da pessoa: a mesma Empresa devolve a mesma lista pro
    admin e pro colaborador. É daqui que a casca monta a navegação — e esconder o menu é só a
    metade educada da negação."""

    acme = await make_company(session, name="Acme")
    widelab = await make_user(session)
    await make_entitlement(
        session,
        organization=acme,
        module_key="refeicoes",
        granted_by=widelab.id,
    )

    admin = await como(role=Role.COMPANY_ADMIN, org=acme)
    colaborador = await como(role=Role.COLLABORATOR, org=acme)

    do_admin = await admin.get(f"/api/organizacoes/{acme.id}/me")
    do_colaborador = await colaborador.get(f"/api/organizacoes/{acme.id}/me")

    assert do_admin.json()["modules"] == ["refeicoes"]
    assert do_colaborador.json()["modules"] == ["refeicoes"]


async def test_me_de_tenant_sem_modulo_devolve_lista_vazia(
    session: AsyncSession,
    como: Como,
) -> None:
    """`[]` significa o que diz — a Empresa não contratou nada."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    response = await admin.get(f"/api/organizacoes/{acme.id}/me")

    assert response.json()["modules"] == []


async def test_so_a_plataforma_liga_o_flag(session: AsyncSession, como: Como) -> None:
    """Ligar o módulo é `modules.write`, que só o `platform_admin` tem. Um `company_admin` que
    pudesse se vender `refeicoes` tornaria o entitlement decorativo."""

    acme = await make_company(session, name="Acme")
    admin_da_empresa = await como(role=Role.COMPANY_ADMIN, org=acme)
    widelab = await como(role=Role.PLATFORM_ADMIN)

    recusado = await admin_da_empresa.put(f"/api/organizacoes/{acme.id}/modulos/refeicoes")
    aceito = await widelab.put(f"/api/organizacoes/{acme.id}/modulos/refeicoes")

    assert recusado.status_code == 403
    assert aceito.status_code == 200


async def test_ligar_o_flag_duas_vezes_e_idempotente(
    session: AsyncSession,
    como: Como,
) -> None:
    """Presença da linha é o sim, e o único de `(organization_id, module_key)` é o que faz o `PUT`
    afirmar um estado em vez de empilhar linha.

    A contagem é no SQL, e não no corpo: a resposta não expõe o `id` do entitlement (é um fato
    sobre o tenant — quem ligou e quando), então "não criou uma segunda linha" só dá pra
    perguntar pra tabela."""

    acme = await make_company(session, name="Acme")
    widelab = await como(role=Role.PLATFORM_ADMIN)

    primeiro = await widelab.put(f"/api/organizacoes/{acme.id}/modulos/refeicoes")
    segundo = await widelab.put(f"/api/organizacoes/{acme.id}/modulos/refeicoes")

    assert primeiro.status_code == 200
    assert segundo.status_code == 200
    assert primeiro.json()["granted_at"] == segundo.json()["granted_at"]

    linhas = await session.execute(
        sa.select(sa.func.count())
        .select_from(ModuleEntitlementModel)
        .where(ModuleEntitlementModel.organization_id == acme.id)
    )
    assert linhas.scalars().one() == 1
