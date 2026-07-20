"""O registro de uso — o coração do módulo.

Critérios 3, 4, 5, 6, 8, 9, 10 e 12 da spec 10."""

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from src.modules.frota.adapters.db.models import VehicleUsage as VehicleUsageModel
from src.modules.frota.domain.entities import DriverStatus, VehicleStatus
from tests.conftest import Como
from tests.factories import make_driver, make_usage, make_user, make_vehicle
from tests.integration.frota.conftest import ComoCondutor

ONTEM = datetime.now(UTC) - timedelta(days=1)


def _iso(momento: datetime) -> str:
    return momento.isoformat()


class TestOGestorLancaEEncerra:
    """Critério 3: o ciclo completo pelo `manager`, cujo papel **não tem capability de kernel
    nenhuma** — todo 2xx aqui veio do `grants` do descritor."""

    async def test_lanca_e_encerra(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)
        base = f"/api/organizacoes/{empresa.id}/frota"

        lancou = await gestor.post(
            f"{base}/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 1000,
                "purpose": "Entrega no centro",
            },
        )
        assert lancou.status_code == 201
        assert lancou.json()["ended_at"] is None
        assert lancou.json()["distance"] is None

        uso_id = lancou.json()["id"]
        encerrou = await gestor.post(
            f"{base}/usos/{uso_id}/encerrar",
            json={"ended_at": _iso(ONTEM + timedelta(hours=3)), "end_odometer": 1150},
        )

        assert encerrou.status_code == 200
        assert encerrou.json()["end_odometer"] == 1150
        assert encerrou.json()["distance"] == 150


class TestOColaboradorLancaOProprio:
    """Critério 4."""

    async def test_lanca_em_seu_proprio_nome(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        pessoa, meu_condutor = await como_condutor(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 500,
            },
        )

        assert resposta.status_code == 201
        assert resposta.json()["driver_id"] == str(meu_condutor.id)

    async def test_com_o_proprio_driver_id_explicito_tambem_vale(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        pessoa, meu_condutor = await como_condutor(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(meu_condutor.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 500,
            },
        )

        assert resposta.status_code == 201

    async def test_com_o_driver_id_de_outro_e_403(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        outro = await make_driver(session, organization=empresa, name="Outro")
        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(outro.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 500,
            },
        )

        assert resposta.status_code == 403

    async def test_sem_condutor_vinculado_e_422(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """422 e não 403: a pessoa **tem** a permissão, o que falta é ela ser condutor
        cadastrado. Um 403 a mandaria procurar permissão que ela já tem."""

        carro = await make_vehicle(session, organization=empresa)
        pessoa = await como(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 500,
            },
        )

        assert resposta.status_code == 422
        assert "condutor" in resposta.json()["message"].lower()

    async def test_o_hr_nao_lanca_nada(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        rh = await como(role=Role.HR, org=empresa)

        resposta = await rh.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 1,
            },
        )

        assert resposta.status_code == 403


class TestEscopoDaListagem:
    """Critério 5: uma rota, escopo por capability."""

    async def test_o_gestor_ve_a_empresa_inteira(
        self,
        como: Como,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro_a = await make_vehicle(session, organization=empresa, plate="AAA1A11")
        carro_b = await make_vehicle(session, organization=empresa, plate="BBB2B22")
        outro = await make_driver(session, organization=empresa, name="Outro")
        quem = await make_user(session)

        _, meu_condutor = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        await make_usage(
            session,
            organization=empresa,
            vehicle=carro_a,
            driver=meu_condutor,
            created_by=quem.id,
        )
        await make_usage(
            session,
            organization=empresa,
            vehicle=carro_b,
            driver=outro,
            created_by=quem.id,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        pagina = (await gestor.get(f"/api/organizacoes/{empresa.id}/frota/usos")).json()

        assert pagina["total"] == 2

    async def test_o_colaborador_ve_so_os_seus(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro_a = await make_vehicle(session, organization=empresa, plate="AAA1A11")
        carro_b = await make_vehicle(session, organization=empresa, plate="BBB2B22")
        outro = await make_driver(session, organization=empresa, name="Outro")
        quem = await make_user(session)

        pessoa, meu_condutor = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        meu = await make_usage(
            session,
            organization=empresa,
            vehicle=carro_a,
            driver=meu_condutor,
            created_by=quem.id,
        )
        await make_usage(
            session,
            organization=empresa,
            vehicle=carro_b,
            driver=outro,
            created_by=quem.id,
        )

        pagina = (await pessoa.get(f"/api/organizacoes/{empresa.id}/frota/usos")).json()

        assert pagina["total"] == 1
        assert pagina["items"][0]["id"] == str(meu.id)

    async def test_o_colaborador_nao_burla_pelo_filtro_de_condutor(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """O `?condutor=` de quem não pode ler tudo é **sobrescrito**, não somado — pedir o
        condutor de outro não pode virar um jeito de vê-lo."""

        carro = await make_vehicle(session, organization=empresa)
        outro = await make_driver(session, organization=empresa, name="Outro")
        quem = await make_user(session)
        await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=outro,
            created_by=quem.id,
        )

        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)

        pagina = (
            await pessoa.get(f"/api/organizacoes/{empresa.id}/frota/usos?condutor={outro.id}")
        ).json()

        assert pagina["total"] == 0

    async def test_sem_condutor_vinculado_a_lista_vem_vazia(
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
        )

        pessoa = await como(role=Role.COLLABORATOR, org=empresa)

        pagina = (await pessoa.get(f"/api/organizacoes/{empresa.id}/frota/usos")).json()

        assert pagina["total"] == 0


class TestSobreposicao:
    """Critério 6, pela rota — o 409 traduzido da violação de exclusão."""

    async def test_periodo_sobreposto_no_mesmo_veiculo_e_409(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)
        base = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)

        await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=base,
            ended_at=base + timedelta(hours=4),
            start_odometer=100,
            end_odometer=200,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(base + timedelta(hours=2)),
                "ended_at": _iso(base + timedelta(hours=6)),
                "start_odometer": 200,
                "end_odometer": 300,
            },
        )

        assert resposta.status_code == 409
        assert "sobrep" in resposta.json()["message"].lower()

    async def test_colide_tambem_com_uma_viagem_aberta(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """A parte que só a constraint de exclusão entrega: `tstzrange(started_at, NULL)` é sem
        limite superior, então a viagem aberta bloqueia qualquer outra do mesmo carro."""

        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)
        base = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)

        await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=base,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(base + timedelta(days=10)),
                "start_odometer": 900,
            },
        )

        assert resposta.status_code == 409

    async def test_o_mesmo_periodo_em_outro_veiculo_e_201(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro_a = await make_vehicle(session, organization=empresa, plate="AAA1A11")
        carro_b = await make_vehicle(session, organization=empresa, plate="BBB2B22")
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)
        base = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)

        await make_usage(
            session,
            organization=empresa,
            vehicle=carro_a,
            driver=motorista,
            created_by=quem.id,
            started_at=base,
            ended_at=base + timedelta(hours=4),
            start_odometer=100,
            end_odometer=200,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro_b.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(base),
                "ended_at": _iso(base + timedelta(hours=4)),
                "start_odometer": 50,
                "end_odometer": 90,
            },
        )

        assert resposta.status_code == 201


class TestEncerrar:
    """Critério 8."""

    async def test_encerrar_duas_vezes_e_409(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)
        uso = await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=ONTEM,
            start_odometer=100,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)
        rota = f"/api/organizacoes/{empresa.id}/frota/usos/{uso.id}/encerrar"
        corpo = {"ended_at": _iso(ONTEM + timedelta(hours=2)), "end_odometer": 200}

        assert (await gestor.post(rota, json=corpo)).status_code == 200

        repetido = await gestor.post(rota, json=corpo)

        assert repetido.status_code == 409

    async def test_patch_numa_viagem_encerrada_segue_aceito(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Corrigir uma viagem encerrada é legítimo — é a diferença entre "fechar" e "corrigir"
        que fez o encerrar virar rota própria."""

        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)
        uso = await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
            started_at=ONTEM,
            ended_at=ONTEM + timedelta(hours=2),
            start_odometer=100,
            end_odometer=200,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.patch(
            f"/api/organizacoes/{empresa.id}/frota/usos/{uso.id}",
            json={"end_odometer": 210},
        )

        assert resposta.status_code == 200
        assert resposta.json()["end_odometer"] == 210

    async def test_o_colaborador_encerra_a_propria(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """O gesto mais frequente do módulo — a única coisa que o Colaborador faz."""

        carro = await make_vehicle(session, organization=empresa)
        quem = await make_user(session)
        pessoa, meu_condutor = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        uso = await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=meu_condutor,
            created_by=quem.id,
            started_at=ONTEM,
            start_odometer=100,
        )

        resposta = await pessoa.post(
            f"/api/organizacoes/{empresa.id}/frota/usos/{uso.id}/encerrar",
            json={"ended_at": _iso(ONTEM + timedelta(hours=1)), "end_odometer": 140},
        )

        assert resposta.status_code == 200

    async def test_o_colaborador_nao_encerra_a_de_outro(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        outro = await make_driver(session, organization=empresa, name="Outro")
        quem = await make_user(session)
        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        alheio = await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=outro,
            created_by=quem.id,
            started_at=ONTEM,
            start_odometer=100,
        )

        resposta = await pessoa.post(
            f"/api/organizacoes/{empresa.id}/frota/usos/{alheio.id}/encerrar",
            json={"ended_at": _iso(ONTEM + timedelta(hours=1)), "end_odometer": 140},
        )

        assert resposta.status_code == 403


class TestRegrasQueOBancoNaoAlcanca:
    """Critério 9: as três validações que vivem na aplicação porque `now()` não entra em `CHECK`
    e um `CHECK` não enxerga outra tabela."""

    async def test_data_futura_e_422(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(datetime.now(UTC) + timedelta(days=1)),
                "start_odometer": 100,
            },
        )

        assert resposta.status_code == 422
        assert "futuro" in resposta.json()["message"].lower()

    async def test_veiculo_inativo_e_422(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa, status=VehicleStatus.INACTIVE)
        motorista = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 100,
            },
        )

        assert resposta.status_code == 422

    async def test_veiculo_em_manutencao_e_422(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa, status=VehicleStatus.MAINTENANCE)
        motorista = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 100,
            },
        )

        assert resposta.status_code == 422

    async def test_condutor_inativo_e_422(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa, status=DriverStatus.INACTIVE)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 100,
            },
        )

        assert resposta.status_code == 422

    async def test_veiculo_de_outra_empresa_e_422(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        from tests.factories import make_company

        outra = await make_company(session, name="Vizinha")
        alheio = await make_vehicle(session, organization=outra)
        motorista = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(alheio.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(ONTEM),
                "start_odometer": 100,
            },
        )

        assert resposta.status_code == 422


class TestApagar:
    """Critério 10: o `DELETE` é do gestor, e o `write_own` não o alcança."""

    async def test_o_gestor_apaga(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)
        uso = await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=motorista,
            created_by=quem.id,
        )

        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.delete(f"/api/organizacoes/{empresa.id}/frota/usos/{uso.id}")

        assert resposta.status_code == 204

    async def test_o_colaborador_nao_apaga_nem_a_propria(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Quem apaga a própria viagem apaga a evidência. Corrigir, sim; sumir, é ato do
        gestor."""

        carro = await make_vehicle(session, organization=empresa)
        quem = await make_user(session)
        pessoa, meu_condutor = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        meu = await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=meu_condutor,
            created_by=quem.id,
        )

        resposta = await pessoa.delete(f"/api/organizacoes/{empresa.id}/frota/usos/{meu.id}")

        assert resposta.status_code == 403

    async def test_o_colaborador_corrige_a_propria(
        self,
        como_condutor: ComoCondutor,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """O contrapositivo do teste acima: `PATCH` **pode**."""

        carro = await make_vehicle(session, organization=empresa)
        quem = await make_user(session)
        pessoa, meu_condutor = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        meu = await make_usage(
            session,
            organization=empresa,
            vehicle=carro,
            driver=meu_condutor,
            created_by=quem.id,
        )

        resposta = await pessoa.patch(
            f"/api/organizacoes/{empresa.id}/frota/usos/{meu.id}",
            json={"purpose": "Corrigido"},
        )

        assert resposta.status_code == 200
        assert resposta.json()["purpose"] == "Corrigido"


class TestRetroativo:
    """Critério 12: lançamento retroativo é cidadão de primeira classe."""

    async def test_viagem_de_dias_atras_e_aceita(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        saida = datetime.now(UTC) - timedelta(days=5)
        volta = saida + timedelta(hours=6)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(saida),
                "ended_at": _iso(volta),
                "start_odometer": 1000,
                "end_odometer": 1250,
            },
        )

        assert resposta.status_code == 201
        assert resposta.json()["distance"] == 250

    async def test_nenhuma_data_foi_preenchida_pelo_relogio_do_servidor(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """A prova de que `started_at`/`ended_at` são digitados: o que voltou (e o que está no
        banco) é exatamente o que foi mandado, não `now()`."""

        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        saida = datetime(2026, 3, 2, 7, 30, tzinfo=UTC)
        volta = datetime(2026, 3, 2, 11, 45, tzinfo=UTC)

        criado = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/usos",
            json={
                "vehicle_id": str(carro.id),
                "driver_id": str(motorista.id),
                "started_at": _iso(saida),
                "ended_at": _iso(volta),
                "start_odometer": 10,
                "end_odometer": 60,
            },
        )
        assert criado.status_code == 201

        gravado = (
            (
                await session.execute(
                    sa.select(VehicleUsageModel).where(VehicleUsageModel.id == criado.json()["id"])
                )
            )
            .scalars()
            .one()
        )

        assert gravado.started_at == saida
        assert gravado.ended_at == volta
        assert gravado.created_at > saida
