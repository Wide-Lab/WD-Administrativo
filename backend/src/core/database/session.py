from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.startup import get_database


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Dependency de sessão do banco. Abre uma sessão por request e fecha ao final.

    Os módulos injetam `SessionDep` e, quando precisam de transação, embrulham a sessão num
    `SQLAlchemyUnitOfWork`."""

    session = get_database().create_session()
    try:
        yield session
    finally:
        await session.close()


SessionDep = Annotated[AsyncSession, Depends(get_session)]
