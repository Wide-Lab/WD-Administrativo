"""O schema da suíte sai de `alembic upgrade head` num banco vazio — e é isso que prende as
migrations.

A `backend/04` registrou que `fk_memberships_user` existe **só** na migration, porque declará-la
no model obrigaria `access` a importar os models do `auth`. Uma suíte que migra do zero é onde
isso aparece: se um `--autogenerate` futuro dropar a FK, o teste abaixo cai."""

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

_TABELAS_ESPERADAS = {
    "users",
    "organizations",
    "partner_agreements",
    "memberships",
    "module_entitlements",
    "invitations",
    # Do primeiro app de negócio (spec 10). Elas entram aqui e não num arquivo do `frota` porque
    # o que se afirma é sobre a **cadeia de migrations**, que é uma só pro repo inteiro.
    "vehicles",
    "drivers",
    "vehicle_usages",
    # Da leitura de hodômetro por foto (spec 11).
    "odometer_readings",
}


async def test_upgrade_head_sobe_do_zero_num_banco_vazio(session: AsyncSession) -> None:
    """O container nasce vazio e a fixture `database_url` roda `upgrade head` nele. Chegar aqui
    com as tabelas de pé já é o teste — mas ele fica explícito pra falhar com nome, e não como
    um erro de fixture no meio de outro teste."""

    result = await session.execute(
        sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    tabelas = set(result.scalars().all())

    assert _TABELAS_ESPERADAS <= tabelas
    assert "alembic_version" in tabelas


async def test_o_banco_esta_na_ultima_migration(session: AsyncSession) -> None:
    result = await session.execute(sa.text("SELECT version_num FROM alembic_version"))

    assert result.scalars().one() == "0007_odometer_readings"


async def test_a_extensao_btree_gist_existe(session: AsyncSession) -> None:
    """A `0006` a cria, e sem ela a constraint de exclusão de `vehicle_usages` não existiria —
    `vehicle_id WITH =` é igualdade de uuid num índice gist, que só o btree_gist ensina."""

    result = await session.execute(
        sa.text("SELECT extname FROM pg_extension WHERE extname = 'btree_gist'")
    )

    assert result.scalars().one_or_none() == "btree_gist"


async def test_a_constraint_de_exclusao_de_vehicle_usages_existe(session: AsyncSession) -> None:
    """A peça central da spec 10, conferida no catálogo do Postgres e não pelo comportamento:
    é o que impede um veículo de estar em dois lugares ao mesmo tempo."""

    result = await session.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'vehicle_usages'::regclass AND contype = 'x'"
        )
    )

    assert "ex_vehicle_usages_no_overlap" in set(result.scalars().all())


async def test_a_organizacao_platform_nasce_semeada(session: AsyncSession) -> None:
    """A migration `0002` semeia a `platform`, e a suíte a reseeda depois de cada `TRUNCATE`.

    Sem ela, todo teste de `platform_admin` mentiria — o vínculo apontaria pra uma organização
    que não existe."""

    result = await session.execute(
        sa.text("SELECT id, name FROM organizations WHERE type = 'platform'")
    )
    row = result.one()

    assert str(row.id) == "01890000-0000-7000-8000-000000000001"
    assert row.name == "Widelab"


async def test_email_e_citext_no_banco(session: AsyncSession) -> None:
    """E-mail é `CITEXT` — a unicidade case-insensitive é do banco, nunca de um `.lower()` na
    aplicação. SQLite não tem isto, e é uma das razões de a suíte falar com Postgres de verdade."""

    result = await session.execute(
        sa.text(
            "SELECT format_type(a.atttypid, a.atttypmod) AS tipo "
            "FROM pg_attribute a "
            "WHERE a.attrelid = 'users'::regclass AND a.attname = 'email'"
        )
    )

    assert result.scalars().one() == "citext"


async def test_a_fk_de_memberships_para_users_existe(session: AsyncSession) -> None:
    """A FK que vive **só** na migration — ver o docstring do módulo."""

    result = await session.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'memberships'::regclass AND contype = 'f'"
        )
    )

    assert "fk_memberships_user" in set(result.scalars().all())


async def test_as_fks_de_odometer_readings_existem(session: AsyncSession) -> None:
    """A `0007` traz **uma** FK que cruza módulo — a sétima da allowlist do `alembic check`.

    `fk_odometer_readings_organization` aponta pra `organizations`, que é do `access`, e por isso
    vive só na migration: um `--autogenerate` vai propor dropá-la, e a resposta é recusar. A de
    veículo é interna ao `frota` e vive no model — está aqui pro teste falar das duas de uma vez,
    e pra a distinção entre elas não virar folclore."""

    result = await session.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'odometer_readings'::regclass AND contype = 'f'"
        )
    )
    fks = set(result.scalars().all())

    assert "fk_odometer_readings_organization" in fks
    assert "fk_odometer_readings_vehicle" in fks


async def test_as_fks_de_vehicle_usages_para_leitura_existem(session: AsyncSession) -> None:
    """As duas FKs compostas que amarram a foto à viagem. Internas ao `frota`, então vivem no
    model **e** na migration — e não entram na allowlist."""

    result = await session.execute(
        sa.text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'vehicle_usages'::regclass AND contype = 'f'"
        )
    )
    fks = set(result.scalars().all())

    assert "fk_vehicle_usages_start_reading" in fks
    assert "fk_vehicle_usages_end_reading" in fks
