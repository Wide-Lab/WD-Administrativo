from typing import Annotated

from fastapi import Query

from src.core.database.session import SessionDep
from src.core.pagination.params import PageParams
from src.core.security import CurrentUser, CurrentUserDep
from src.core.tenancy import CurrentOrganization, CurrentOrganizationDep
from src.modules.access.adapters.db.unit_of_work import AccessUnitOfWork


def get_unit_of_work(session: SessionDep) -> AccessUnitOfWork:
    """Embrulha a sessão da requisição numa unit of work, como a fundação prevê."""

    return AccessUnitOfWork(session=session)


def get_page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


async def require_platform_admin(user: CurrentUserDep) -> CurrentUser:
    """Guard de plataforma — **hoje só exige sessão**.

    Papel é `memberships` + papéis, spec 04, e nada disso existe no schema ainda; a spec 03
    previu subir com o guard permissivo e apertar quando a 04 entrar. Existir já como
    dependency é o que faz o aperto ser uma linha aqui, e não uma varredura pelas rotas.

    TODO(spec 04): exigir vínculo `platform_admin` na organização plataforma — senão 403."""

    return user


async def require_company_admin(organization: CurrentOrganizationDep) -> CurrentOrganization:
    """Guard de admin da Empresa — **hoje só exige acesso à organização do path**.

    O 403 de organização inalcançável já vale (vem de `current_organization`); o que falta é
    exigir o *papel* `company_admin` dentro dela.

    TODO(spec 04): exigir vínculo com papel `company_admin` — senão 403."""

    return organization
