from typing import Annotated

from fastapi import Depends

from src.core.authz import require_permission
from src.core.pagination.params import PageParams
from src.core.security import CurrentUser
from src.core.tenancy import CurrentOrganization
from src.modules.access.adapters.db.unit_of_work import AccessUnitOfWork
from src.modules.access.adapters.http.dependencies import (
    get_page_params,
    get_unit_of_work,
    require_platform_admin,
)
from src.modules.access.domain.permissions import PLATFORM_PERMISSIONS

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

AgreementWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.AGREEMENTS_WRITE)),
]
"""Substitui o `CompanyAdminDep` permissivo da spec 03, que só exigia alcançar a organização.

Note que o guard passou a nomear a **capability**, não o papel: a rota diz o que precisa
poder fazer, e o mapa papel→permissões decide quem pode. Era `company_admin` no texto da
spec 03 e continua sendo na prática — `agreements.write` só está nesse papel —, mas mudar
isso agora é editar um `frozenset`, não caçar rotas."""

MemberReaderDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.MEMBERS_READ)),
]

MemberWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.MEMBERS_WRITE)),
]
