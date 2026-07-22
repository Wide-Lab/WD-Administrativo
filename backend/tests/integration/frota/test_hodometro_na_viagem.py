"""A foto amarrada à viagem, e servida de volta.

Critérios 9 e 10 da spec 11."""

import uuid
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.storage import LocalDirectoryStorage
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import (
    make_company,
    make_driver,
    make_reading,
    make_usage,
    make_user,
    make_vehicle,
)
from tests.integration.frota.conftest import ComoCondutor, Motor, foto_jpeg

ONTEM = datetime(2026, 7, 21, 8, 0, tzinfo=UTC)


def usos(org: OrganizationModel) -> str:
    return f"/api/organizacoes/{org.id}/frota/usos"


class TestLancarComLeitura:
    """Critério 9: a referência é aceita, e as três conferências recusam com 422."""

    async def test_lancar_com_leitura_valida_grava_start_reading_id(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=45_180)
        condutor = await make_driver(session, organization=empresa)

        leitura = (
            await gestor.post(
                f"/api/organizacoes/{empresa.id}/frota/veiculos/{veiculo.id}"
                "/hodometro/leituras",
                files={"foto": ("painel.jpg", foto_jpeg(), "image/jpeg")},
            )
        ).json()

        resposta = await gestor.post(
            usos(empresa),
            json={
                "vehicle_id": str(veiculo.id),
                "driver_id": str(condutor.id),
                "started_at": ONTEM.isoformat(),
                "start_odometer": 45_210,
                "leitura_saida_id": leitura["id"],
            },
        )

        assert resposta.status_code == 201
        assert resposta.json()["start_reading_id"] == leitura["id"]

        gravado = (
            await session.execute(
                sa.text("SELECT start_reading_id FROM vehicle_usages WHERE id = :id"),
                {"id": resposta.json()["id"]},
            )
        ).scalar_one()
        assert str(gravado) == leitura["id"]

    async def test_sem_leitura_nenhuma_segue_201(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """A foto é **opcional e continua sendo**: um módulo que a exigisse teria trocado uma
        folha de papel por uma catraca."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)

        resposta = await gestor.post(
            usos(empresa),
            json={
                "vehicle_id": str(veiculo.id),
                "driver_id": str(condutor.id),
                "started_at": ONTEM.isoformat(),
                "start_odometer": 45_210,
            },
        )

        assert resposta.status_code == 201
        assert resposta.json()["start_reading_id"] is None

    async def test_leitura_de_outro_veiculo_e_422(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """Anexar a foto do carro A à viagem do carro B faria a evidência mentir."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        outro_veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        leitura = await make_reading(
            session,
            organization=empresa,
            vehicle=outro_veiculo,
            created_by=quem.id,
        )

        resposta = await gestor.post(
            usos(empresa),
            json={
                "vehicle_id": str(veiculo.id),
                "driver_id": str(condutor.id),
                "started_at": ONTEM.isoformat(),
                "start_odometer": 45_210,
                "leitura_saida_id": str(leitura.id),
            },
        )

        assert resposta.status_code == 422
        assert "outro veículo" in resposta.json()["message"]

    async def test_leitura_ja_apontada_e_422(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """A evidência que serve pra duas viagens não serve pra nenhuma."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        leitura = await make_reading(
            session,
            organization=empresa,
            vehicle=veiculo,
            created_by=quem.id,
        )
        primeira = await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=ONTEM - timedelta(days=3),
            ended_at=ONTEM - timedelta(days=3) + timedelta(hours=2),
            end_odometer=45_000,
        )
        primeira.start_reading_id = leitura.id
        await session.commit()

        resposta = await gestor.post(
            usos(empresa),
            json={
                "vehicle_id": str(veiculo.id),
                "driver_id": str(condutor.id),
                "started_at": ONTEM.isoformat(),
                "start_odometer": 45_210,
                "leitura_saida_id": str(leitura.id),
            },
        )

        assert resposta.status_code == 422
        assert "outra viagem" in resposta.json()["message"]

    async def test_leitura_de_outra_empresa_e_422(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """Sai de graça do repositório tenant-scoped: leitura de outra Empresa simplesmente não é
        encontrada. **422 e não 404** — quem manda o id não está navegando pra um recurso, está
        anexando um dado a um corpo que o servidor recusa por inteiro."""

        outra = await make_company(session, name="Empresa Vizinha")
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        veiculo_alheio = await make_vehicle(session, organization=outra)
        quem = await make_user(session)

        alheia = await make_reading(
            session,
            organization=outra,
            vehicle=veiculo_alheio,
            created_by=quem.id,
        )

        resposta = await gestor.post(
            usos(empresa),
            json={
                "vehicle_id": str(veiculo.id),
                "driver_id": str(condutor.id),
                "started_at": ONTEM.isoformat(),
                "start_odometer": 45_210,
                "leitura_saida_id": str(alheia.id),
            },
        )

        assert resposta.status_code == 422


class TestEncerrarComLeitura:
    async def test_encerrar_grava_end_reading_id(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        viagem = await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=ONTEM,
        )
        leitura = await make_reading(
            session,
            organization=empresa,
            vehicle=veiculo,
            created_by=quem.id,
        )

        resposta = await gestor.post(
            f"{usos(empresa)}/{viagem.id}/encerrar",
            json={
                "ended_at": (ONTEM + timedelta(hours=3)).isoformat(),
                "end_odometer": 45_400,
                "leitura_chegada_id": str(leitura.id),
            },
        )

        assert resposta.status_code == 200
        assert resposta.json()["end_reading_id"] == str(leitura.id)

    async def test_encerrar_sem_leitura_segue_funcionando(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        viagem = await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=ONTEM,
        )

        resposta = await gestor.post(
            f"{usos(empresa)}/{viagem.id}/encerrar",
            json={
                "ended_at": (ONTEM + timedelta(hours=3)).isoformat(),
                "end_odometer": 45_400,
            },
        )

        assert resposta.status_code == 200
        assert resposta.json()["end_reading_id"] is None


class TestPatchNaoAceitaLeitura:
    async def test_o_campo_e_ignorado_pelo_patch(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """Corrigir a foto de uma viagem já lançada é caso raro o bastante pra esperar quem peça
        (spec 11), então `UpdateUsageRequest` não tem o campo — e o Pydantic o descarta em vez de
        gravá-lo pela porta dos fundos."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        viagem = await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=ONTEM,
        )
        leitura = await make_reading(
            session,
            organization=empresa,
            vehicle=veiculo,
            created_by=quem.id,
        )

        resposta = await gestor.patch(
            f"{usos(empresa)}/{viagem.id}",
            json={"purpose": "Entrega", "leitura_saida_id": str(leitura.id)},
        )

        assert resposta.status_code == 200
        assert resposta.json()["start_reading_id"] is None


class TestServirAFoto:
    """Critério 10: os bytes saem **pela API**, com o `content-type` gravado, e o escopo nega
    com 404."""

    async def test_devolve_os_bytes_com_o_content_type_original(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        bytes_da_foto = foto_jpeg()

        leitura = (
            await gestor.post(
                f"/api/organizacoes/{empresa.id}/frota/veiculos/{veiculo.id}"
                "/hodometro/leituras",
                files={"foto": ("painel.jpg", bytes_da_foto, "image/jpeg")},
            )
        ).json()

        viagem = (
            await gestor.post(
                usos(empresa),
                json={
                    "vehicle_id": str(veiculo.id),
                    "driver_id": str(condutor.id),
                    "started_at": ONTEM.isoformat(),
                    "start_odometer": 45_210,
                    "leitura_saida_id": leitura["id"],
                },
            )
        ).json()

        resposta = await gestor.get(f"{usos(empresa)}/{viagem['id']}/hodometro/saida")

        assert resposta.status_code == 200
        assert resposta.content == bytes_da_foto
        assert resposta.headers["content-type"] == "image/jpeg"

    async def test_viagem_sem_foto_de_chegada_e_404(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        viagem = await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=ONTEM,
        )

        resposta = await gestor.get(f"{usos(empresa)}/{viagem.id}/hodometro/chegada")

        assert resposta.status_code == 404

    async def test_collaborator_nao_ve_a_foto_de_viagem_de_outro(
        self,
        como_condutor: ComoCondutor,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
        como: Como,
    ) -> None:
        """**404, e não 403** — o mesmo escopo de `GET /usos`. Um 403 confirmaria que a viagem de
        outro condutor existe, que é justamente o que o escopo esconde."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)
        outro_condutor = await make_driver(session, organization=empresa, name="Outra Pessoa")

        leitura = (
            await gestor.post(
                f"/api/organizacoes/{empresa.id}/frota/veiculos/{veiculo.id}"
                "/hodometro/leituras",
                files={"foto": ("painel.jpg", foto_jpeg(), "image/jpeg")},
            )
        ).json()

        viagem = (
            await gestor.post(
                usos(empresa),
                json={
                    "vehicle_id": str(veiculo.id),
                    "driver_id": str(outro_condutor.id),
                    "started_at": ONTEM.isoformat(),
                    "start_odometer": 45_210,
                    "leitura_saida_id": leitura["id"],
                },
            )
        ).json()

        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.get(f"{usos(empresa)}/{viagem['id']}/hodometro/saida")

        assert resposta.status_code == 404

    async def test_collaborator_ve_a_foto_da_propria_viagem(
        self,
        como_condutor: ComoCondutor,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
    ) -> None:
        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa)

        leitura = (
            await pessoa.post(
                f"/api/organizacoes/{empresa.id}/frota/veiculos/{veiculo.id}"
                "/hodometro/leituras",
                files={"foto": ("painel.jpg", foto_jpeg(), "image/jpeg")},
            )
        ).json()

        viagem = (
            await pessoa.post(
                usos(empresa),
                json={
                    "vehicle_id": str(veiculo.id),
                    "started_at": ONTEM.isoformat(),
                    "start_odometer": 45_210,
                    "leitura_saida_id": leitura["id"],
                },
            )
        ).json()

        resposta = await pessoa.get(f"{usos(empresa)}/{viagem['id']}/hodometro/saida")

        assert resposta.status_code == 200

    async def test_lado_invalido_e_422(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """`{saida|chegada}` é enum na rota: qualquer outra coisa nem chega ao use case."""

        gestor = await como(role=papel_gestor, org=empresa)

        resposta = await gestor.get(f"{usos(empresa)}/{uuid.uuid7()}/hodometro/lateral")

        assert resposta.status_code == 422
