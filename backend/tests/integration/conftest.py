"""O que vale só pros testes que falam com o banco.

**O `clean_database` mora aqui, e não no `conftest.py` raiz, porque é `autouse`.** Autouse na
raiz o ligaria também em `tests/unit/`, que é regra pura — e aí `pytest tests/unit` passaria a
exigir Docker pra testar um `frozenset`. A divisão `unit/`/`integration/` da spec 07 não é
cerimônia: é o que faz o `unit/` rodar em milissegundos, e ela só é verdade se a dependência de
banco parar nesta porta. Ver `Como ficou` da spec."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
import sqlalchemy as sa

from src.modules.access.adapters.db.models import Organization as OrganizationModel


@pytest.fixture(autouse=True)
async def clean_database(
    database_url: str,
    platform_seed: dict[str, Any],
) -> AsyncIterator[None]:
    """`TRUNCATE` de tudo + reseed da organização `platform`, **antes** de cada teste.

    `TRUNCATE`, e não uma transação externa com rollback, apesar de mais lento: o truque do
    rollback mascara justamente o que a spec 06 precisa que seja testado — a **atomicidade** do
    auto-cadastro de Parceiro. Verificar que uma falha não deixa organização órfã exige commit e
    rollback de verdade, não savepoint aninhado dentro do harness. Velocidade aqui vale menos que
    poder testar a propriedade cara.

    O reseed é obrigatório porque o `TRUNCATE` leva a `platform` junto, e todo teste de
    `platform_admin` depende dela."""

    from src.core.database.startup import get_database

    # Sessão, e não `engine.begin()`: o `Database` do `core` expõe a engine pela porta `Engine`,
    # que só sabe `dispose()`. A limpeza entra pela mesma porta que a app usa pra escrever.
    async with get_database().create_session() as db_session:
        tables = (
            (
                await db_session.execute(
                    sa.text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                    )
                )
            )
            .scalars()
            .all()
        )
        if tables:
            alvos = ", ".join(f'"{table}"' for table in tables)
            await db_session.execute(sa.text(f"TRUNCATE TABLE {alvos} RESTART IDENTITY CASCADE"))

        await db_session.execute(sa.insert(OrganizationModel).values(**platform_seed))
        await db_session.commit()

    yield
