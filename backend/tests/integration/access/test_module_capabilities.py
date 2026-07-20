"""O caminho completo da spec 09: uma capability declarada por um módulo chega a um papel.

**Sobre o módulo de prova:** `refeicoes` e `frota` declaram `grants={}` — de propósito, até as
fases 2 e 3 —, então não há no app um único endpoint que exercite o mecanismo de ponta a ponta.
O `smoke` daqui é o módulo descartável que a spec pede, a mesma receita que as specs 04 e 05
usaram pra provar `require_permission` e `mount_module`. Ele some quando a frota (`backend/10`)
existir de verdade.

**Por que `registry_isolado` em todo teste:** `_modules` é global de processo. Sem restaurá-lo, o
`smoke` vaza pro `GET /modulos` dos outros testes e pra soma do `PermissionReader` — e a ordem da
suíte vira parte do resultado."""

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.modules import ModuleDescriptor, ModuleNav
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import make_company, make_entitlement, make_user

SMOKE = ModuleDescriptor(
    key="smoke",
    name="Smoke",
    personas=["company_admin"],
    grants={Role.MANAGER.value: frozenset({"smoke.reports.read"})},
    nav=ModuleNav(label="Smoke", path="/smoke"),
)
"""Concede a **um** papel só, e a um que não tem nenhuma capability de kernel (`manager` sai
vazio de `PERMISSIONS_BY_ROLE`). É o que faz o 200 do critério 1 só poder ter vindo do
mecanismo desta spec."""

ROTA = "/api/organizacoes/{org_id}/smoke/relatorios"


@pytest.fixture(scope="session")
async def rota_smoke(database_url: str) -> AsyncIterator[str]:
    """Pendura a rota do `smoke` na app, atrás dos **dois** guards de verdade.

    Só a rota é de sessão; o **registro** do descritor é por teste (`smoke_registrado`), porque é
    ele que vaza. Montar por `mount_module` faria as duas coisas de uma vez e registraria o módulo
    pelo resto do processo."""

    from fastapi import APIRouter, Depends

    from src.core.authz import require_permission
    from src.core.modules import require_module
    from src.main import app

    router = APIRouter()

    @router.get(
        f"/organizacoes/{{orgId}}/{SMOKE.key}/relatorios",
        dependencies=[
            Depends(require_module(SMOKE.key)),
            Depends(require_permission("smoke.reports.read")),
        ],
    )
    async def relatorios() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router, prefix="/api")

    yield ROTA


@pytest.fixture
def smoke_registrado(registry_isolado: None) -> ModuleDescriptor:
    """Põe o `smoke` no registry só pela duração de um teste — e o tira depois."""

    from src.core.modules import register_module

    register_module(SMOKE)
    return SMOKE


async def test_capability_de_modulo_chega_ao_papel(
    session: AsyncSession,
    como: Como,
    rota_smoke: str,
    smoke_registrado: ModuleDescriptor,
) -> None:
    """**O critério 1, e o ponto inteiro da spec.**

    `manager` não tem uma única capability em `PERMISSIONS_BY_ROLE` — o 200 aqui não pode ter
    vindo do mapa do kernel. Veio do descritor, somado pelo `PermissionReader`, sem nenhuma linha
    no `access`: é isso que destrava o primeiro endpoint do primeiro app de negócio."""

    acme = await make_company(session, name="Acme")
    widelab = await make_user(session)
    await make_entitlement(
        session,
        organization=acme,
        module_key=SMOKE.key,
        granted_by=widelab.id,
    )
    gerente = await como(role=Role.MANAGER, org=acme)

    response = await gerente.get(rota_smoke.format(org_id=acme.id))

    assert response.status_code == 200


async def test_papel_sem_a_concessao_e_negado(
    session: AsyncSession,
    como: Como,
    client: AsyncClient,
    rota_smoke: str,
    smoke_registrado: ModuleDescriptor,
) -> None:
    """O critério 2: a concessão é **por papel**, não "quem tem o módulo entra".

    O `collaborator` está na mesma Empresa e enxerga o mesmo entitlement; o que lhe falta é a
    capability. Sem este par, o 200 do teste acima poderia ser um guard que não nega ninguém."""

    acme = await make_company(session, name="Acme")
    widelab = await make_user(session)
    await make_entitlement(
        session,
        organization=acme,
        module_key=SMOKE.key,
        granted_by=widelab.id,
    )
    colaborador = await como(role=Role.COLLABORATOR, org=acme)

    negado = await colaborador.get(rota_smoke.format(org_id=acme.id))
    sem_sessao = await client.get(rota_smoke.format(org_id=acme.id))

    assert negado.status_code == 403
    assert sem_sessao.status_code == 401


async def test_capability_de_modulo_nao_passa_por_cima_do_entitlement(
    session: AsyncSession,
    como: Como,
    rota_smoke: str,
    smoke_registrado: ModuleDescriptor,
) -> None:
    """**O critério 3, e a ordem que a spec 05 fixou.**

    Mesmo `manager` do critério 1, mesma capability — e 403, porque a Empresa não contratou. Ter
    a permissão de um módulo não é ter o módulo: `require_module` pergunta o que o *tenant*
    comprou e vem antes. Um mecanismo que somasse capability e por isso liberasse a rota
    entregaria de graça o que não foi vendido."""

    acme = await make_company(session, name="Acme")
    gerente = await como(role=Role.MANAGER, org=acme)

    response = await gerente.get(rota_smoke.format(org_id=acme.id))

    assert response.status_code == 403


async def test_me_traz_a_capability_de_modulo_de_quem_a_recebe(
    session: AsyncSession,
    como: Como,
    smoke_registrado: ModuleDescriptor,
) -> None:
    """O critério 4: a casca desenha a tela a partir do `/me`, e o guard nega a partir do reader.

    As duas contas precisam bater — se o `/me` omitisse a capability, o menu esconderia uma rota
    que responde 200; se a inventasse, prometeria uma que responde 403."""

    acme = await make_company(session, name="Acme")
    gerente = await como(role=Role.MANAGER, org=acme)
    colaborador = await como(role=Role.COLLABORATOR, org=acme)

    do_gerente = await gerente.get(f"/api/organizacoes/{acme.id}/me")
    do_colaborador = await colaborador.get(f"/api/organizacoes/{acme.id}/me")

    assert "smoke.reports.read" in do_gerente.json()["permissions"]
    assert "smoke.reports.read" not in do_colaborador.json()["permissions"]


async def test_platform_admin_nao_recebe_capability_de_modulo(
    session: AsyncSession,
    como: Como,
    smoke_registrado: ModuleDescriptor,
) -> None:
    """**O critério 7, e a assimetria que ele protege.**

    A Widelab alcança a Acme (o `/me` responde 200) e segue com as capabilities de kernel de
    plataforma — mas sem a do módulo. Somar aqui contrabandearia pela porta de dentro o que
    `validate_module_grants` recusa na subida: a `platform` não é `company`, não pode nem
    contratar o módulo, e a permissão morreria no `require_module` de qualquer jeito.

    A Widelab conserta vínculo e vende módulo. Ela não opera a frota do cliente."""

    acme = await make_company(session, name="Acme")
    widelab = await como(role=Role.PLATFORM_ADMIN)
    await make_entitlement(
        session,
        organization=acme,
        module_key=SMOKE.key,
        granted_by=(await make_user(session)).id,
    )

    response = await widelab.get(f"/api/organizacoes/{acme.id}/me")

    permissions = response.json()["permissions"]
    assert response.status_code == 200
    assert "modules.write" in permissions
    assert "smoke.reports.read" not in permissions


async def test_refeicoes_e_frota_seguem_vendaveis(
    session: AsyncSession,
    como: Como,
) -> None:
    """O critério 8: trocar `permissions=[]` por `grants={}` não mexeu no que já funcionava.

    Sem `smoke_registrado` de propósito — este é o catálogo **real** do app, e é o teste que a
    fixture de isolamento protege: sem ela, o `smoke` de outro teste apareceria aqui.

    **Metade deste teste deixou de valer na spec 10, e a mudança é o ponto.** Ele nasceu
    afirmando que `FROTA.permissions == frozenset()` — verdade enquanto a frota era um
    placeholder em `src/api/modules.py`. Hoje ela é um módulo de verdade, com sete capabilities e
    descritor próprio em `src/modules/frota/module.py`, e é exatamente isso que a `09` existia
    pra destravar. O que o critério 8 afirmava de fato — *o mecanismo novo não quebrou a venda* —
    segue de pé e continua testado aqui; quem ainda declara `grants={}` é só `refeicoes`."""

    acme = await make_company(session, name="Acme")
    widelab = await como(role=Role.PLATFORM_ADMIN)

    ligou = await widelab.put(f"/api/organizacoes/{acme.id}/modulos/frota")
    catalogo = await widelab.get(f"/api/organizacoes/{acme.id}/modulos")

    assert ligou.status_code == 200

    corpo = catalogo.json()
    chaves = {modulo["key"] for modulo in corpo["catalog"]}
    assert {"refeicoes", "frota"} <= chaves
    assert "smoke" not in chaves

    from src.api.modules import REFEICOES
    from src.modules.frota.module import FROTA

    assert REFEICOES.permissions == frozenset()
    assert FROTA.permissions != frozenset()
