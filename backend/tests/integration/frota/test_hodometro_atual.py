"""O `current_odometer` de `VehicleResponse` — critério 7 da spec 11.

**Derivado, nunca coluna.** Guardá-lo seria uma segunda fonte da verdade, pronta pra divergir da
primeira no primeiro lançamento retroativo fora de ordem — e é isso que os testes de "viagem
aberta" e "duas viagens encerradas" põem à prova.

Todos os cenários entram por `INSERT` direto (as factories), como a spec manda: o que se afirma é
o que a **query** deriva, não o que a rota de lançamento aceita."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import make_driver, make_user, make_vehicle

BASE = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)


def veiculos(org: OrganizationModel) -> str:
    return f"/api/organizacoes/{org.id}/frota/veiculos"


class ContadorDeSelects:
    """Conta os `SELECT` que saem pela engine — o instrumento do teste de N+1.

    Escuta a classe `Engine` do SQLAlchemy, e não uma instância: a engine da app é criada por um
    `lru_cache` no `core` e o teste não tem como alcançá-la sem furar a porta."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def __call__(self, *args: object) -> None:
        self.statements.append(str(args[2]))

    @property
    def selects(self) -> int:
        return len([s for s in self.statements if s.lstrip().upper().startswith("SELECT")])


@pytest.fixture
def contando_selects() -> Iterator[ContadorDeSelects]:
    contador = ContadorDeSelects()
    event.listen(Engine, "before_cursor_execute", contador)
    yield contador
    event.remove(Engine, "before_cursor_execute", contador)


class TestCurrentOdometer:
    async def test_veiculo_sem_viagem_devolve_o_initial_odometer(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=12_000)

        resposta = await gestor.get(f"{veiculos(empresa)}/{veiculo.id}")

        assert resposta.json()["current_odometer"] == 12_000

    async def test_depois_de_duas_viagens_e_o_maior_end_odometer(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        from tests.factories import make_usage

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=12_000)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        for dia, (saida, chegada) in enumerate([(12_000, 12_300), (12_300, 12_850)]):
            await make_usage(
                session,
                organization=empresa,
                vehicle=veiculo,
                driver=condutor,
                created_by=quem.id,
                started_at=BASE + timedelta(days=dia),
                ended_at=BASE + timedelta(days=dia, hours=4),
                start_odometer=saida,
                end_odometer=chegada,
            )

        resposta = await gestor.get(f"{veiculos(empresa)}/{veiculo.id}")

        assert resposta.json()["current_odometer"] == 12_850

    async def test_viagem_aberta_maior_que_todos_vence(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """**Um carro na rua já rodou.** Ignorar o `start_odometer` de uma viagem aberta faria o
        prior de um veículo em viagem apontar pra antes da saída — e a leitura por foto acusaria
        um delta que não existe."""

        from tests.factories import make_usage

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=12_000)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=BASE,
            ended_at=BASE + timedelta(hours=4),
            start_odometer=12_000,
            end_odometer=12_300,
        )
        await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=BASE + timedelta(days=2),
            start_odometer=12_900,
        )

        resposta = await gestor.get(f"{veiculos(empresa)}/{veiculo.id}")

        assert resposta.json()["current_odometer"] == 12_900

    async def test_initial_odometer_maior_que_as_viagens_vence(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """O `GREATEST` inclui o `initial_odometer` de propósito: um carro cadastrado com 80.000
        km e cujas únicas viagens registradas são retroativas de quando ele tinha 12.000 não
        "voltou" pra 12.000."""

        from tests.factories import make_usage

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=80_000)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=BASE,
            ended_at=BASE + timedelta(hours=4),
            start_odometer=12_000,
            end_odometer=12_300,
        )

        resposta = await gestor.get(f"{veiculos(empresa)}/{veiculo.id}")

        assert resposta.json()["current_odometer"] == 80_000

    async def test_a_listagem_tambem_traz_o_campo(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        await make_vehicle(session, organization=empresa, initial_odometer=12_000)

        resposta = await gestor.get(veiculos(empresa))

        assert resposta.json()["items"][0]["current_odometer"] == 12_000

    async def test_o_post_devolve_o_campo(
        self,
        como: Como,
        empresa: OrganizationModel,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)

        resposta = await gestor.post(
            veiculos(empresa),
            json={
                "plate": "NOV0A11",
                "brand": "Fiat",
                "model": "Strada",
                "initial_odometer": 500,
            },
        )

        assert resposta.status_code == 201
        assert resposta.json()["current_odometer"] == 500

    async def test_o_patch_devolve_o_campo_ja_derivado(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
    ) -> None:
        """O `create`/`update` do `core` monta a entidade só do model, e ali o `current_odometer`
        seria um palpite — o `initial_odometer` de um carro que já tem viagens. Por isso o
        repositório relê pelo caminho com join depois de escrever."""

        from tests.factories import make_usage

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=12_000)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=BASE,
            ended_at=BASE + timedelta(hours=4),
            start_odometer=12_000,
            end_odometer=12_850,
        )

        resposta = await gestor.patch(
            f"{veiculos(empresa)}/{veiculo.id}",
            json={"brand": "Fiat Profissional"},
        )

        assert resposta.json()["current_odometer"] == 12_850


class TestSemNPlusUm:
    async def test_a_listagem_nao_cresce_em_queries_com_o_numero_de_veiculos(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
        contando_selects: ContadorDeSelects,
    ) -> None:
        """O critério pede "uma query" pra 20 veículos. O que se mede é o que importa: que a
        contagem **não dependa** do número de linhas.

        Um `current_odometer` derivado por consulta-por-veículo passaria em todos os testes acima
        e só apareceria em produção, no dia em que a frota tivesse 200 carros."""

        gestor = await como(role=papel_gestor, org=empresa)

        for _ in range(2):
            await make_vehicle(session, organization=empresa)

        contando_selects.statements.clear()
        await gestor.get(f"{veiculos(empresa)}?page_size=100")
        com_dois = contando_selects.selects

        for _ in range(18):
            await make_vehicle(session, organization=empresa)

        contando_selects.statements.clear()
        resposta = await gestor.get(f"{veiculos(empresa)}?page_size=100")
        com_vinte = contando_selects.selects

        assert len(resposta.json()["items"]) == 20
        assert com_vinte == com_dois

    async def test_a_pagina_de_veiculos_sai_de_uma_query_de_dados(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
        contando_selects: ContadorDeSelects,
    ) -> None:
        """A contagem e a página são dois `SELECT` em `vehicles` — o `count` da paginação é
        herdado do `core` e vale pra todas as listagens do projeto. O que esta spec não podia
        acrescentar era um terceiro por linha."""

        gestor = await como(role=papel_gestor, org=empresa)
        for _ in range(5):
            await make_vehicle(session, organization=empresa)

        contando_selects.statements.clear()
        await gestor.get(veiculos(empresa))

        em_vehicles = [
            s
            for s in contando_selects.statements
            if s.lstrip().upper().startswith("SELECT") and "vehicles" in s
        ]
        assert len(em_vehicles) == 2


class TestOPriorDaLeitura:
    async def test_o_ultimo_hodometro_da_leitura_e_o_current_odometer(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        papel_gestor: Role,
        motor: object,
        storage: object,
    ) -> None:
        """É o que transforma a resposta da leitura de um número solto numa frase conferível."""

        from tests.factories import make_usage
        from tests.integration.frota.conftest import foto_jpeg

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=12_000)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=BASE,
            ended_at=BASE + timedelta(hours=4),
            start_odometer=12_000,
            end_odometer=12_850,
        )

        resposta = await gestor.post(
            f"{veiculos(empresa)}/{veiculo.id}/hodometro/leituras",
            files={"foto": ("painel.jpg", foto_jpeg(), "image/jpeg")},
        )

        assert resposta.json()["ultimo_hodometro"] == 12_850


async def test_o_hodometro_atual_nao_e_coluna(session: AsyncSession) -> None:
    """A afirmação que sustenta todo o resto, conferida no catálogo do Postgres.

    Se alguém "otimizar" isto pra uma coluna um dia, este teste cai — e é onde a conversa sobre
    a segunda fonte da verdade precisa acontecer de novo."""

    result = await session.execute(
        sa.text(
            "SELECT attname FROM pg_attribute "
            "WHERE attrelid = 'vehicles'::regclass AND attnum > 0 AND NOT attisdropped"
        )
    )

    assert "current_odometer" not in set(result.scalars().all())
