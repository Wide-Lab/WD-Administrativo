from typing import Annotated

from fastapi import Depends, Query

from src.core.database.session import SessionDep
from src.core.exceptions import ForbiddenError
from src.core.pagination.params import PageParams
from src.core.security import CurrentUser, CurrentUserDep
from src.modules.access.adapters.db.membership_reader import SqlAlchemyMembershipReader
from src.modules.access.adapters.db.unit_of_work import AccessUnitOfWork


def get_unit_of_work(session: SessionDep) -> AccessUnitOfWork:
    """Embrulha a sessão da requisição numa unit of work, como a fundação prevê."""

    return AccessUnitOfWork(session=session)


def get_membership_reader(session: SessionDep) -> SqlAlchemyMembershipReader:
    """O leitor de vínculo dos guards.

    Guard lê, não escreve: por isso um reader sobre a `SessionDep`, e não a unit of work. Se
    o guard entrasse na uow, o `__aexit__` dela fecharia a sessão antes de a rota usá-la."""

    return SqlAlchemyMembershipReader(session)


def get_page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


async def require_platform_admin(
    user: CurrentUserDep,
    memberships: Annotated[SqlAlchemyMembershipReader, Depends(get_membership_reader)],
) -> CurrentUser:
    """Guard de plataforma: exige vínculo `platform_admin` ativo na organização `platform`.

    É o único guard que **não** passa por `require_permission`, e a razão é estrutural:
    `require_permission` resolve a permissão dentro da organização do path, e as rotas de
    plataforma (`POST`/`GET /api/organizacoes`) não têm `orgId` — provisionar um tenant é
    justamente o ato que acontece antes de existir tenant. Aqui a pergunta não é "nesta
    organização", é "na Widelab"."""

    if not await memberships.is_platform_admin(user.id):
        raise ForbiddenError("Ação restrita à administração da plataforma.")

    return user
