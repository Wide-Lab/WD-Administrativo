"""As invariantes que moram no **banco**, verificadas por `INSERT` direto — por fora da aplicação.

Critério 7 da spec 10, e a mesma receita com que a `05` provou o "só Empresa contrata": o que se
está afirmando aqui **não** é que a rota valida, é que o banco impede. Um `if` em Python passaria
verde nestes testes se eles fossem feitos pela API, e a invariante seguiria sem rede."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_company, make_driver, make_partner, make_user, make_vehicle

ONTEM = datetime.now(UTC) - timedelta(days=1)
HOJE = datetime.now(UTC)


async def _insert_usage(session: AsyncSession, **valores: object) -> None:
    """Um `INSERT` cru em `vehicle_usages`, sem passar por model nem por rota."""

    colunas = ", ".join(valores)
    binds = ", ".join(f":{nome}" for nome in valores)
    await session.execute(
        sa.text(f"INSERT INTO vehicle_usages ({colunas}) VALUES ({binds})"),
        valores,
    )
    await session.commit()


class TestFkCompostaCruzandoTenant:
    """O carro da Empresa A com o motorista da Empresa B é impossível **no banco**.

    Em multi-tenant com banco compartilhado, uma FK simples aceitaria a mistura, e o vazamento
    apareceria num relatório meses depois."""

    async def test_veiculo_de_uma_empresa_com_condutor_de_outra_viola_a_fk(
        self,
        session: AsyncSession,
    ) -> None:
        empresa_a = await make_company(session, name="A")
        empresa_b = await make_company(session, name="B")
        carro_da_a = await make_vehicle(session, organization=empresa_a)
        motorista_da_b = await make_driver(session, organization=empresa_b)
        quem = await make_user(session)

        with pytest.raises(IntegrityError) as erro:
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa_a.id,
                vehicle_id=carro_da_a.id,
                driver_id=motorista_da_b.id,
                started_at=ONTEM,
                start_odometer=100,
                created_by=quem.id,
            )

        assert "fk_vehicle_usages_driver" in str(erro.value)

    async def test_uso_carimbado_na_organizacao_errada_viola_a_fk(
        self,
        session: AsyncSession,
    ) -> None:
        """Nem trocando o `organization_id` do próprio uso: a FK é composta com ele."""

        empresa_a = await make_company(session, name="A")
        empresa_b = await make_company(session, name="B")
        carro = await make_vehicle(session, organization=empresa_a)
        motorista = await make_driver(session, organization=empresa_a)
        quem = await make_user(session)

        with pytest.raises(IntegrityError):
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa_b.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=ONTEM,
                start_odometer=100,
                created_by=quem.id,
            )


class TestFecharEAtomico:
    """`ck_vehicle_usages_closed_together`: ou fecha inteira, ou não fechou.

    Uma viagem com hora de volta e sem hodômetro final é meia-linha que estraga o relatório e
    ninguém repara."""

    async def test_ended_at_sem_end_odometer_viola_o_check(
        self,
        session: AsyncSession,
    ) -> None:
        empresa = await make_company(session)
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        with pytest.raises(IntegrityError) as erro:
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=ONTEM,
                ended_at=HOJE,
                start_odometer=100,
                created_by=quem.id,
            )

        assert "ck_vehicle_usages_closed_together" in str(erro.value)

    async def test_end_odometer_sem_ended_at_tambem_viola(
        self,
        session: AsyncSession,
    ) -> None:
        empresa = await make_company(session)
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        with pytest.raises(IntegrityError) as erro:
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=ONTEM,
                start_odometer=100,
                end_odometer=200,
                created_by=quem.id,
            )

        assert "ck_vehicle_usages_closed_together" in str(erro.value)


class TestPeriodoEHodometro:
    async def test_volta_antes_da_saida_viola_o_check(self, session: AsyncSession) -> None:
        empresa = await make_company(session)
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        with pytest.raises(IntegrityError) as erro:
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=HOJE,
                ended_at=ONTEM,
                start_odometer=100,
                end_odometer=200,
                created_by=quem.id,
            )

        assert "ck_vehicle_usages_period" in str(erro.value)

    async def test_hodometro_final_menor_que_inicial_viola_o_check(
        self,
        session: AsyncSession,
    ) -> None:
        empresa = await make_company(session)
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        with pytest.raises(IntegrityError) as erro:
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=ONTEM,
                ended_at=HOJE,
                start_odometer=500,
                end_odometer=100,
                created_by=quem.id,
            )

        assert "ck_vehicle_usages_odometer" in str(erro.value)


class TestSoEmpresaTemFrota:
    """A FK composta contra `organizations(id, type)` com o tipo fixado em coluna gerada — o
    mesmo truque de `module_entitlements`. Um Parceiro não tem frota, e quem garante é o banco."""

    @pytest.mark.parametrize("tabela", ["vehicles", "drivers"])
    async def test_parceiro_nao_tem_frota(
        self,
        session: AsyncSession,
        tabela: str,
    ) -> None:
        parceiro = await make_partner(session, name="Restaurante")

        colunas = {
            "vehicles": "(id, organization_id, plate, brand, model, initial_odometer)",
            "drivers": "(id, organization_id, name)",
        }[tabela]
        valores = {
            "vehicles": "(:id, :org, 'AAA1A11', 'Fiat', 'Uno', 0)",
            "drivers": "(:id, :org, 'Alguém')",
        }[tabela]

        with pytest.raises(IntegrityError) as erro:
            await session.execute(
                sa.text(f"INSERT INTO {tabela} {colunas} VALUES {valores}"),
                {"id": uuid.uuid7(), "org": parceiro.id},
            )
            await session.commit()

        assert f"fk_{tabela}_organization" in str(erro.value)


class TestSobreposicaoDePeriodo:
    """`ex_vehicle_usages_no_overlap` — a peça central da spec, no nível do banco.

    Por `INSERT` direto e não pela rota: o que se afirma é que o **banco** impede o veículo de
    estar em dois lugares ao mesmo tempo, não que a aplicação lembra de checar."""

    async def test_dois_periodos_sobrepostos_no_mesmo_veiculo_violam_a_exclusao(
        self,
        session: AsyncSession,
    ) -> None:
        empresa = await make_company(session)
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        base = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
        await _insert_usage(
            session,
            id=uuid.uuid7(),
            organization_id=empresa.id,
            vehicle_id=carro.id,
            driver_id=motorista.id,
            started_at=base,
            ended_at=base + timedelta(hours=4),
            start_odometer=100,
            end_odometer=200,
            created_by=quem.id,
        )

        with pytest.raises(IntegrityError) as erro:
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=base + timedelta(hours=2),
                ended_at=base + timedelta(hours=6),
                start_odometer=200,
                end_odometer=300,
                created_by=quem.id,
            )

        assert "ex_vehicle_usages_no_overlap" in str(erro.value)

    async def test_uma_viagem_aberta_bloqueia_qualquer_outra_do_mesmo_veiculo(
        self,
        session: AsyncSession,
    ) -> None:
        """`tstzrange(started_at, NULL)` é **sem limite superior** — é o que faz a exclusão
        entregar de graça o índice parcial de "um veículo, uma viagem aberta"."""

        empresa = await make_company(session)
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        base = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
        await _insert_usage(
            session,
            id=uuid.uuid7(),
            organization_id=empresa.id,
            vehicle_id=carro.id,
            driver_id=motorista.id,
            started_at=base,
            start_odometer=100,
            created_by=quem.id,
        )

        with pytest.raises(IntegrityError) as erro:
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=base + timedelta(days=30),
                start_odometer=900,
                created_by=quem.id,
            )

        assert "ex_vehicle_usages_no_overlap" in str(erro.value)

    async def test_o_mesmo_periodo_em_outro_veiculo_e_aceito(
        self,
        session: AsyncSession,
    ) -> None:
        """A exclusão é por `vehicle_id WITH =`: dois carros diferentes rodam ao mesmo tempo."""

        empresa = await make_company(session)
        carro_a = await make_vehicle(session, organization=empresa, plate="AAA1A11")
        carro_b = await make_vehicle(session, organization=empresa, plate="BBB2B22")
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        base = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
        for carro in (carro_a, carro_b):
            await _insert_usage(
                session,
                id=uuid.uuid7(),
                organization_id=empresa.id,
                vehicle_id=carro.id,
                driver_id=motorista.id,
                started_at=base,
                ended_at=base + timedelta(hours=4),
                start_odometer=100,
                end_odometer=200,
                created_by=quem.id,
            )

        total = await session.scalar(sa.text("SELECT count(*) FROM vehicle_usages"))
        assert total == 2

    async def test_periodos_encostados_nao_se_sobrepoem(
        self,
        session: AsyncSession,
    ) -> None:
        """`tstzrange` é `[)` por default: a viagem que termina às 12h e a que começa às 12h
        **não** colidem. Sem isso, o uso normal da frota (devolver e outro pegar) seria 409."""

        empresa = await make_company(session)
        carro = await make_vehicle(session, organization=empresa)
        motorista = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        base = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)
        await _insert_usage(
            session,
            id=uuid.uuid7(),
            organization_id=empresa.id,
            vehicle_id=carro.id,
            driver_id=motorista.id,
            started_at=base,
            ended_at=base + timedelta(hours=4),
            start_odometer=100,
            end_odometer=200,
            created_by=quem.id,
        )

        await _insert_usage(
            session,
            id=uuid.uuid7(),
            organization_id=empresa.id,
            vehicle_id=carro.id,
            driver_id=motorista.id,
            started_at=base + timedelta(hours=4),
            ended_at=base + timedelta(hours=8),
            start_odometer=200,
            end_odometer=260,
            created_by=quem.id,
        )

        total = await session.scalar(sa.text("SELECT count(*) FROM vehicle_usages"))
        assert total == 2
