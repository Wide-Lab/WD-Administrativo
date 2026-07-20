"""O contrato de plugagem: o que a frota provou sobre o mecanismo das specs 05 e 09.

Critérios 1 e 2 da spec 10."""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como

_SRC = Path(__file__).resolve().parents[3] / "src"


class TestAFrotaNaoImportaOutroModulo:
    """Critério 1, verificável por leitura de import — e por isso é teste, não inspeção manual:
    um `from src.modules.access...` acrescentado daqui a seis meses quebra a suíte, não passa
    despercebido num code review."""

    @pytest.mark.parametrize("proibido", ["src.modules.auth", "src.modules.access"])
    def test_nenhum_arquivo_da_frota_importa_o_kernel(self, proibido: str) -> None:
        ofensores = [
            arquivo.relative_to(_SRC).as_posix()
            for arquivo in (_SRC / "modules" / "frota").rglob("*.py")
            if proibido in arquivo.read_text(encoding="utf-8")
        ]

        assert ofensores == [], (
            f"A frota é um app de negócio: ela depende só de `src.core` e dos contracts do "
            f"kernel. Estes arquivos importam `{proibido}`: {ofensores}"
        )

    def test_a_frota_importa_o_core(self) -> None:
        """O contrapositivo: o teste acima passaria num módulo vazio."""

        modulo = _SRC / "modules" / "frota" / "module.py"
        assert "src.core.modules" in modulo.read_text(encoding="utf-8")


class TestEntitlement:
    """Critério 2: sem o flag, 403 em qualquer rota; com ele, 200 — sem deploy."""

    @pytest.mark.parametrize(
        "rota",
        [
            "veiculos",
            "condutores",
            "usos",
            "relatorios/quilometragem?de=2026-01-01T00:00:00Z&ate=2026-12-31T00:00:00Z",
        ],
    )
    async def test_sem_entitlement_toda_rota_nega(
        self,
        como: Como,
        empresa_sem_frota: OrganizationModel,
        rota: str,
    ) -> None:
        """Um `company_admin` — papel e permissão corretos — leva 403 porque a **Empresa** não
        contratou. A negação é do backend, não do frontend."""

        cliente = await como(role=Role.COMPANY_ADMIN, org=empresa_sem_frota)

        resposta = await cliente.get(f"/api/organizacoes/{empresa_sem_frota.id}/frota/{rota}")

        assert resposta.status_code == 403
        assert "módulo" in resposta.json()["message"]

    async def test_ligar_o_flag_abre_a_rota_sem_deploy(
        self,
        como: Como,
        client: AsyncClient,
        session: AsyncSession,
        empresa_sem_frota: OrganizationModel,
    ) -> None:
        """O ciclo inteiro pela API: 403, `PUT /modulos/frota` como `platform_admin`, 200.

        É o critério 2 literal — "ligado o flag, o mesmo request responde 200, sem deploy" — e é
        o que faz o entitlement ser um fato comercial e não uma constante de build."""

        gestor = await como(role=Role.MANAGER, org=empresa_sem_frota)
        rota = f"/api/organizacoes/{empresa_sem_frota.id}/frota/veiculos"

        assert (await gestor.get(rota)).status_code == 403

        plataforma = await como(role=Role.PLATFORM_ADMIN)
        ligou = await plataforma.put(f"/api/organizacoes/{empresa_sem_frota.id}/modulos/frota")
        assert ligou.status_code == 200

        assert (await gestor.get(rota)).status_code == 200

    async def test_desligar_o_flag_volta_a_negar(
        self,
        como: Como,
        empresa: OrganizationModel,
    ) -> None:
        gestor = await como(role=Role.MANAGER, org=empresa)
        rota = f"/api/organizacoes/{empresa.id}/frota/veiculos"

        assert (await gestor.get(rota)).status_code == 200

        plataforma = await como(role=Role.PLATFORM_ADMIN)
        assert (
            await plataforma.delete(f"/api/organizacoes/{empresa.id}/modulos/frota")
        ).status_code == 204

        assert (await gestor.get(rota)).status_code == 403

    async def test_platform_admin_nao_fura_o_entitlement(
        self,
        como: Como,
        empresa_sem_frota: OrganizationModel,
    ) -> None:
        """`require_module` **não afrouxa pra ninguém** — diferente de `require_permission`.
        Entitlement é fato comercial, não privilégio: a Widelab não abre por dentro o que não
        vendeu."""

        plataforma = await como(role=Role.PLATFORM_ADMIN)

        resposta = await plataforma.get(f"/api/organizacoes/{empresa_sem_frota.id}/frota/veiculos")

        assert resposta.status_code == 403

    async def test_sem_sessao_e_401(
        self,
        client: AsyncClient,
        empresa: OrganizationModel,
    ) -> None:
        resposta = await client.get(f"/api/organizacoes/{empresa.id}/frota/veiculos")

        assert resposta.status_code == 401


class TestCapabilityChegaAoPapel:
    """Critério 3, o lado do mecanismo: o `manager` autoriza pelo `grants` do descritor, sem
    nenhuma linha em `PERMISSIONS_BY_ROLE`."""

    async def test_o_me_traz_as_capabilities_de_frota(
        self,
        como: Como,
        empresa: OrganizationModel,
    ) -> None:
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.get(f"/api/organizacoes/{empresa.id}/me")

        permissoes = resposta.json()["permissions"]
        assert "frota.vehicles.write" in permissoes
        assert "frota.usages.read" in permissoes
        assert resposta.json()["modules"] == ["frota"]

    async def test_o_collaborator_recebe_so_as_duas(
        self,
        como: Como,
        empresa: OrganizationModel,
    ) -> None:
        pessoa = await como(role=Role.COLLABORATOR, org=empresa)

        permissoes = (await pessoa.get(f"/api/organizacoes/{empresa.id}/me")).json()["permissions"]

        assert "frota.vehicles.read" in permissoes
        assert "frota.usages.write_own" in permissoes
        assert "frota.vehicles.write" not in permissoes
        assert "frota.drivers.read" not in permissoes

    async def test_o_hr_nao_recebe_nada_de_frota(
        self,
        como: Como,
        empresa: OrganizationModel,
    ) -> None:
        rh = await como(role=Role.HR, org=empresa)

        permissoes = (await rh.get(f"/api/organizacoes/{empresa.id}/me")).json()["permissions"]

        assert not [p for p in permissoes if p.startswith("frota.")]

    async def test_o_platform_admin_nao_recebe_capability_de_modulo(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Módulo não concede à Plataforma — nem por dentro, na soma do `PermissionReader`."""

        plataforma = await como(role=Role.PLATFORM_ADMIN)

        permissoes = (await plataforma.get(f"/api/organizacoes/{empresa.id}/me")).json()

        assert not [p for p in permissoes["permissions"] if p.startswith("frota.")]
