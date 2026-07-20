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

InvitationReaderDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.INVITATIONS_READ)),
]
"""O guard de quem **vê** os convites: `company_admin`, `hr` e `partner_admin` (spec 08).

Separado do writer pelo mesmo desenho que separa `members.read` de `members.write` — e a
separação tem consequência de verdade: um papel de leitura futura enxerga a fila sem poder
convidar. Um `finance` ou um `collaborator` leva 403 aqui."""

InvitationWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.INVITATIONS_WRITE)),
]
"""O guard de quem convida **e revoga**: `company_admin`, `hr` e, desde a spec 08,
`partner_admin`.

É ele que fecha o critério 4 da spec 06 sem um `if` na rota — a permissão é resolvida **na
organização do path**, então um `hr` da Acme que aponte o `orgId` da Globex leva 403 pelo mesmo
caminho de sempre. O papel dele na própria Empresa não viaja pra fora dela.

O `partner_admin` entrar aqui é o que faz um **Parceiro crescer** (spec 08), e não custou rota
nova: ele usa as mesmas três de convite. Quem garante que ele só convida papel de Parceiro é o
`CHECK` do banco, não um `if` — a mesma divisão de trabalho da spec 06."""

MemberReaderDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.MEMBERS_READ)),
]

MemberWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.MEMBERS_WRITE)),
]

ModuleReaderDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.MODULES_READ)),
]

ModuleWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(PLATFORM_PERMISSIONS.MODULES_WRITE)),
]
"""O "só `platform_admin` altera entitlement" da spec, sem `if` de papel na rota.

Nenhum papel além de `platform_admin` tem `modules.write`, e o `SqlAlchemyMembershipReader`
soma as permissões de plataforma em **qualquer** organização do path — é o mesmo mecanismo que
já deixa a Widelab consertar o vínculo de uma Empresa onde ela não tem vínculo. Um
`company_admin` na própria Empresa leva 403 aqui."""
