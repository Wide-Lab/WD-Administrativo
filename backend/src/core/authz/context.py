from collections.abc import Awaitable, Callable
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import SessionDep
from src.core.exceptions import ForbiddenError
from src.core.security import CurrentUser, CurrentUserDep, UserId
from src.core.tenancy import CurrentOrganization, CurrentOrganizationDep, OrganizationId

type Permission = str
"""Uma capability — `agreements.write`, `members.read`. É `str` de propósito: o `core` não é
dono do catálogo, só do mecanismo. O kernel (`access`) declara as permissões da plataforma e
cada módulo de negócio declarará as suas (spec 05); se o `core` guardasse o enum, todo módulo
novo o obrigaria a mudar, e a seta voltaria a apontar pra fora."""


class PermissionReader(Protocol):
    """Porta de leitura de permissão. Existe pro `core` resolver `require_permission` sem
    importar `access` — quem a implementa é o `access`, dono de `memberships` e do mapa
    papel→permissões. Mesmo padrão do `UserReader` (spec 02) e do `OrganizationReader`
    (spec 03)."""

    async def get_permissions(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> frozenset[Permission]:
        """As permissões de `user_id` **dentro de** `organization_id`. Vazio se não houver
        vínculo — autorização é sempre dentro de uma organização."""
        ...


type PermissionReaderFactory = Callable[[AsyncSession], PermissionReader]

_permission_reader_factory: PermissionReaderFactory | None = None


def set_permission_reader_factory(factory: PermissionReaderFactory) -> None:
    """Liga a implementação de `PermissionReader` ao `core`. Chamada uma vez em `mount_routes`
    pelo kernel `access`."""

    global _permission_reader_factory
    _permission_reader_factory = factory


async def get_permission_reader(session: SessionDep) -> PermissionReader:
    if _permission_reader_factory is None:
        raise RuntimeError(
            "Nenhum PermissionReader registrado. O kernel `access` deve chamar "
            "set_permission_reader_factory() em mount_routes."
        )
    return _permission_reader_factory(session)


PermissionReaderDep = Annotated[PermissionReader, Depends(get_permission_reader)]


def require_permission(
    permission: Permission,
) -> Callable[
    [CurrentUser, CurrentOrganization, PermissionReader],
    Awaitable[CurrentOrganization],
]:
    """Guard de autorização: resolve o papel do `current_user` na organização do path e nega
    com 403 se a permissão faltar. Devolve a organização ativa, pra a rota consumi-la sem
    declarar `CurrentOrganizationDep` de novo.

        AgreementWriterDep = Annotated[
            CurrentOrganization, Depends(require_permission("agreements.write"))
        ]

    Compõe com `current_organization`, que já nega o tenant inalcançável — daí um endpoint
    ganhar as duas negações de uma vez. Na spec 05 compõe também com `require_module`: um
    endpoint de app de negócio tipicamente exige as duas.

    Mora no `core` justamente pra os módulos de negócio a consumirem sem importar `access`."""

    async def dependency(
        user: CurrentUserDep,
        organization: CurrentOrganizationDep,
        reader: PermissionReaderDep,
    ) -> CurrentOrganization:
        granted = await reader.get_permissions(
            user_id=user.id,
            organization_id=organization.id,
        )
        if permission not in granted:
            raise ForbiddenError("Você não tem permissão para esta ação.")

        return organization

    return dependency
