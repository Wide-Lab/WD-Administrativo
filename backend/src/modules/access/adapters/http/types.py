from typing import Annotated

from fastapi import Depends

from src.core.pagination.params import PageParams
from src.core.security import CurrentUser
from src.core.tenancy import CurrentOrganization
from src.modules.access.adapters.db.unit_of_work import AccessUnitOfWork
from src.modules.access.adapters.http.dependencies import (
    get_page_params,
    get_unit_of_work,
    require_company_admin,
    require_platform_admin,
)

UnitOfWorkDep = Annotated[
    AccessUnitOfWork,
    Depends(get_unit_of_work),
]

PageParamsDep = Annotated[
    PageParams,
    Depends(get_page_params),
]

PlatformAdminDep = Annotated[
    CurrentUser,
    Depends(require_platform_admin),
]

CompanyAdminDep = Annotated[
    CurrentOrganization,
    Depends(require_company_admin),
]
