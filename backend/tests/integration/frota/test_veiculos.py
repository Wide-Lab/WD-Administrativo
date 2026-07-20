"""Veículos: cadastro, edição, placa única por Empresa e a ausência de `DELETE`.

Critérios 3, 9 e 10 da spec 10."""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from src.modules.frota.adapters.db.models import Vehicle as VehicleModel
from src.modules.frota.domain.entities import VehicleStatus
from tests.conftest import Como
from tests.factories import make_company, make_entitlement, make_user, make_vehicle

CARRO = {"plate": "ABC1D23", "brand": "Fiat", "model": "Strada", "initial_odometer": 12000}


class TestCadastro:
    async def test_o_gestor_cadastra(self, como: Como, empresa: OrganizationModel) -> None:
        """Critério 3: o `manager` cadastra veículo — e ele **não tem nenhuma capability de
        kernel**, então este 201 só pode ter vindo do `grants` do descritor."""

        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(f"/api/organizacoes/{empresa.id}/frota/veiculos", json=CARRO)

        assert resposta.status_code == 201
        assert resposta.json()["plate"] == "ABC1D23"
        assert resposta.json()["organization_id"] == str(empresa.id)

    async def test_o_collaborator_nao_cadastra(
        self, como: Como, empresa: OrganizationModel
    ) -> None:
        """Critério 3, o outro lado: ele lê veículo (precisa escolher o carro) e não escreve."""

        pessoa = await como(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.post(f"/api/organizacoes/{empresa.id}/frota/veiculos", json=CARRO)

        assert resposta.status_code == 403

    async def test_o_collaborator_le(self, como: Como, empresa: OrganizationModel) -> None:
        pessoa = await como(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.get(f"/api/organizacoes/{empresa.id}/frota/veiculos")

        assert resposta.status_code == 200

    async def test_o_hr_nao_le_nem_escreve(self, como: Como, empresa: OrganizationModel) -> None:
        rh = await como(role=Role.HR, org=empresa)

        assert (await rh.get(f"/api/organizacoes/{empresa.id}/frota/veiculos")).status_code == 403
        assert (
            await rh.post(f"/api/organizacoes/{empresa.id}/frota/veiculos", json=CARRO)
        ).status_code == 403

    async def test_a_placa_e_normalizada_em_maiusculas(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """A normalização é da aplicação — e é ela que faz o `UNIQUE` significar o que promete."""

        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/veiculos",
            json={**CARRO, "plate": "  xyz9k88 "},
        )

        assert resposta.json()["plate"] == "XYZ9K88"

        gravada = await session.scalar(
            sa.select(VehicleModel.plate).where(VehicleModel.id == resposta.json()["id"])
        )
        assert gravada == "XYZ9K88"


class TestPlacaDuplicada:
    """Critério 9, a parte da placa."""

    async def test_placa_repetida_na_mesma_empresa_e_409(
        self, como: Como, empresa: OrganizationModel
    ) -> None:
        gestor = await como(role=Role.MANAGER, org=empresa)
        rota = f"/api/organizacoes/{empresa.id}/frota/veiculos"

        assert (await gestor.post(rota, json=CARRO)).status_code == 201

        repetida = await gestor.post(rota, json=CARRO)

        assert repetida.status_code == 409
        assert "ABC1D23" in repetida.json()["message"]

    async def test_a_normalizacao_pega_a_duplicata_disfarcada(
        self, como: Como, empresa: OrganizationModel
    ) -> None:
        """`abc1d23` e `ABC1D23` são o mesmo carro. Sem normalizar, seriam duas linhas."""

        gestor = await como(role=Role.MANAGER, org=empresa)
        rota = f"/api/organizacoes/{empresa.id}/frota/veiculos"

        assert (await gestor.post(rota, json=CARRO)).status_code == 201

        disfarcada = await gestor.post(rota, json={**CARRO, "plate": "abc1d23"})

        assert disfarcada.status_code == 409

    async def test_a_mesma_placa_em_outra_empresa_e_aceita(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Frota terceirizada e carro vendido de uma Empresa pra outra são reais — o único é por
        `(organization_id, plate)`, não global."""

        gestor = await como(role=Role.MANAGER, org=empresa)
        assert (
            await gestor.post(f"/api/organizacoes/{empresa.id}/frota/veiculos", json=CARRO)
        ).status_code == 201

        outra = await make_company(session, name="Outra Empresa")
        quem_ligou = await make_user(session)
        await make_entitlement(
            session, organization=outra, module_key="frota", granted_by=quem_ligou.id
        )
        gestor_da_outra = await como(role=Role.MANAGER, org=outra)

        resposta = await gestor_da_outra.post(
            f"/api/organizacoes/{outra.id}/frota/veiculos", json=CARRO
        )

        assert resposta.status_code == 201


class TestEscopoDeTenant:
    async def test_veiculo_de_outra_empresa_nao_aparece_na_lista(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        outra = await make_company(session, name="Vizinha")
        await make_vehicle(session, organization=outra, plate="ZZZ0Z00")
        meu = await make_vehicle(session, organization=empresa, plate="MEU1M11")

        gestor = await como(role=Role.MANAGER, org=empresa)
        itens = (await gestor.get(f"/api/organizacoes/{empresa.id}/frota/veiculos")).json()["items"]

        assert [item["plate"] for item in itens] == ["MEU1M11"]
        assert str(meu.id) in [item["id"] for item in itens]

    async def test_veiculo_de_outra_empresa_e_404_e_nao_403(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """403 confirmaria que o veículo existe. A resposta não pode virar oráculo."""

        outra = await make_company(session, name="Vizinha")
        alheio = await make_vehicle(session, organization=outra)

        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.get(f"/api/organizacoes/{empresa.id}/frota/veiculos/{alheio.id}")

        assert resposta.status_code == 404


class TestEdicaoENaoExclusao:
    """Critério 10, a parte do veículo."""

    async def test_desativar_e_um_patch(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.patch(
            f"/api/organizacoes/{empresa.id}/frota/veiculos/{carro.id}",
            json={"status": "inactive"},
        )

        assert resposta.status_code == 200
        assert resposta.json()["status"] == "inactive"

    async def test_nao_existe_delete_de_veiculo(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Apagar levaria junto o histórico, que é o produto."""

        carro = await make_vehicle(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.delete(f"/api/organizacoes/{empresa.id}/frota/veiculos/{carro.id}")

        assert resposta.status_code == 405

    async def test_o_veiculo_desativado_continua_na_lista(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Some da escolha na tela, não do sistema."""

        await make_vehicle(
            session, organization=empresa, plate="OFF1O11", status=VehicleStatus.INACTIVE
        )
        gestor = await como(role=Role.MANAGER, org=empresa)

        itens = (await gestor.get(f"/api/organizacoes/{empresa.id}/frota/veiculos")).json()["items"]

        assert "OFF1O11" in [item["plate"] for item in itens]

    async def test_corpo_vazio_e_422(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.patch(
            f"/api/organizacoes/{empresa.id}/frota/veiculos/{carro.id}", json={}
        )

        assert resposta.status_code == 422
