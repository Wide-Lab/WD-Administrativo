"""O relatório de quilometragem — a pergunta que a folha de papel na portaria existe pra
responder.

Critério 11 da spec 10."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import make_driver, make_usage, make_user, make_vehicle
from tests.integration.frota.conftest import ComoCondutor

JANEIRO = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
PERIODO = "de=2026-01-01T00:00:00Z&ate=2026-01-31T23:59:59Z"


class TestSoma:
    async def test_soma_por_veiculo(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa, plate="ABC1D23")
        motorista = await make_driver(session, organization=empresa, name="Ana")
        quem = await make_user(session)

        for dia, (inicio, fim) in enumerate([(1000, 1150), (1150, 1200)]):
            await make_usage(
                session,
                organization=empresa,
                vehicle=carro,
                driver=motorista,
                created_by=quem.id,
                started_at=JANEIRO + timedelta(days=dia),
                ended_at=JANEIRO + timedelta(days=dia, hours=3),
                start_odometer=inicio,
                end_odometer=fim,
            )

        gestor = await como(role=Role.MANAGER, org=empresa)
        corpo = (
            await gestor.get(
                f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem?{PERIODO}"
            )
        ).json()

        assert corpo["group_by"] == "veiculo"
        assert len(corpo["groups"]) == 1
        grupo = corpo["groups"][0]
        assert grupo["label"] == "ABC1D23"
        assert grupo["total_km"] == 200
        assert grupo["closed_usages"] == 2
        assert grupo["open_usages"] == 0

    async def test_agrupa_por_condutor_quando_pedido(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro_a = await make_vehicle(session, organization=empresa, plate="AAA1A11")
        carro_b = await make_vehicle(session, organization=empresa, plate="BBB2B22")
        motorista = await make_driver(session, organization=empresa, name="Ana")
        quem = await make_user(session)

        for dia, carro in enumerate([carro_a, carro_b]):
            await make_usage(
                session,
                organization=empresa,
                vehicle=carro,
                driver=motorista,
                created_by=quem.id,
                started_at=JANEIRO + timedelta(days=dia),
                ended_at=JANEIRO + timedelta(days=dia, hours=2),
                start_odometer=0,
                end_odometer=70,
            )

        gestor = await como(role=Role.MANAGER, org=empresa)
        corpo = (
            await gestor.get(
                f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem"
                f"?{PERIODO}&agrupar_por=condutor"
            )
        ).json()

        assert corpo["group_by"] == "condutor"
        assert len(corpo["groups"]) == 1
        assert corpo["groups"][0]["label"] == "Ana"
        assert corpo["groups"][0]["total_km"] == 140


class TestUsoAbertoNuncaViraZero:
    """A regra que impede o relatório de mentir pra baixo."""

    async def test_o_aberto_conta_a_parte(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa, plate="ABC1D23")
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=JANEIRO,
            ended_at=JANEIRO + timedelta(hours=3),
            start_odometer=1000,
            end_odometer=1150,
        )
        await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=JANEIRO + timedelta(days=2),
            start_odometer=1150,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        grupo = (
            await gestor.get(
                f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem?{PERIODO}"
            )
        ).json()["groups"][0]

        assert grupo["total_km"] == 150
        assert grupo["closed_usages"] == 1
        assert grupo["open_usages"] == 1


class TestPeriodoEEscopo:
    async def test_uso_fora_do_periodo_nao_entra(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=datetime(2026, 2, 10, 8, 0, tzinfo=UTC),
            ended_at=datetime(2026, 2, 10, 12, 0, tzinfo=UTC),
            start_odometer=0,
            end_odometer=999,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        corpo = (
            await gestor.get(
                f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem?{PERIODO}"
            )
        ).json()

        assert corpo["groups"] == []

    async def test_o_veiculo_desativado_continua_no_relatorio_do_periodo_em_que_rodou(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Critério 10, a outra metade: um carro vendido some da escolha e **não** some do
        histórico."""

        carro = await make_vehicle(session, organization=empresa, plate="OFF1O11")
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)
        await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=JANEIRO,
            ended_at=JANEIRO + timedelta(hours=2),
            start_odometer=0,
            end_odometer=80,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        assert (
            await gestor.patch(
                f"/api/organizacoes/{empresa.id}/frota/veiculos/{carro.id}",
                json={"status": "inactive"},
            )
        ).status_code == 200

        corpo = (
            await gestor.get(
                f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem?{PERIODO}"
            )
        ).json()

        assert corpo["groups"][0]["label"] == "OFF1O11"
        assert corpo["groups"][0]["total_km"] == 80

    async def test_de_e_ate_sao_obrigatorios(self, como: Como, empresa: OrganizationModel) -> None:
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.get(
            f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem"
        )

        assert resposta.status_code == 422


class TestPermissao:
    async def test_o_colaborador_nao_ve_o_relatorio(
        self,
        como_condutor: ComoCondutor,
        empresa: OrganizationModel,
    ) -> None:
        """O relatório é da Empresa inteira, e exige `frota.usages.read` — que o `collaborator`
        não tem. É a diferença entre ele e o `GET /usos`, cujo escopo é dado."""

        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.get(
            f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem?{PERIODO}"
        )

        assert resposta.status_code == 403

    async def test_o_gestor_ve(self, como: Como, empresa: OrganizationModel) -> None:
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.get(
            f"/api/organizacoes/{empresa.id}/frota/relatorios/quilometragem?{PERIODO}"
        )

        assert resposta.status_code == 200
