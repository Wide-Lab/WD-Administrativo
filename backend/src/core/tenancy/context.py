import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Protocol

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import SessionDep
from src.core.exceptions import ForbiddenError
from src.core.security import CurrentUserDep, UserId

type OrganizationId = uuid.UUID


class OrganizationType(StrEnum):
    """O tipo de uma organização — definido na criação e **imutável**.

    Mora no `core`, e não no `access`, porque é vocabulário do contrato de tenancy: quem
    consome `current_organization` precisa saber se está numa Empresa ou num Parceiro sem
    importar `access`. Quem é dono da *tabela* `organizations` continua sendo o `access`."""

    PLATFORM = "platform"
    """A Widelab como operadora do SaaS. Exatamente uma linha."""

    COMPANY = "company"
    """Um tenant (Empresa). A Widelab-como-cliente é uma linha `company`, distinta da
    `platform`."""

    PARTNER = "partner"
    """Um Parceiro (restaurante) — organização de primeiro nível, atende N Empresas."""


@dataclass(frozen=True, slots=True)
class CurrentOrganization:
    """A organização ativa da requisição, já validada contra quem fez a requisição.

    É o contrato que os módulos de negócio consomem pra escopar dados por tenant — o análogo
    de `CurrentUser` pro eixo de organização."""

    id: OrganizationId
    type: OrganizationType
    name: str


class OrganizationReader(Protocol):
    """Porta de leitura de organização acessível. Existe pro `core` resolver
    `current_organization` sem importar `access` — quem a implementa é o `access`, dono da
    tabela `organizations` e (na spec 04) dos vínculos."""

    async def get_accessible(
        self,
        user_id: UserId,
        organization_id: OrganizationId,
    ) -> CurrentOrganization | None:
        """Devolve a organização se `user_id` puder agir nela; `None` caso contrário —
        e `None` vira 403 em `current_organization`."""
        ...


type OrganizationReaderFactory = Callable[[AsyncSession], OrganizationReader]

_organization_reader_factory: OrganizationReaderFactory | None = None


def set_organization_reader_factory(factory: OrganizationReaderFactory) -> None:
    """Liga a implementação de `OrganizationReader` ao `core`. Chamada uma vez em
    `mount_routes` pelo kernel `access` — é o que mantém a seta de dependência apontando pra
    dentro (`core` nunca importa um módulo). Mesmo padrão do `UserReader` (spec 02)."""

    global _organization_reader_factory
    _organization_reader_factory = factory


async def get_organization_reader(session: SessionDep) -> OrganizationReader:
    if _organization_reader_factory is None:
        raise RuntimeError(
            "Nenhum OrganizationReader registrado. O kernel `access` deve chamar "
            "set_organization_reader_factory() em mount_routes."
        )
    return _organization_reader_factory(session)


OrganizationReaderDep = Annotated[OrganizationReader, Depends(get_organization_reader)]


async def current_organization(
    user: CurrentUserDep,
    reader: OrganizationReaderDep,
    org_id: Annotated[uuid.UUID, Path(alias="orgId")],
) -> CurrentOrganization:
    """Dependency de tenant: lê o `orgId` do **path**, confere que quem fez a requisição pode
    agir naquela organização e devolve a organização; 403 se não puder.

    O tenant viaja no path e nunca em header ou sessão: a requisição é autoexplicativa, não
    existe "organização default" implícita a adivinhar, e a URL do frontend é compartilhável
    por organização. Trocar de contexto é navegar pra outro `orgId`.

    Mora no `core` justamente pra os módulos de negócio a consumirem sem importar `access`."""

    organization = await reader.get_accessible(user_id=user.id, organization_id=org_id)
    if organization is None:
        raise ForbiddenError("Você não tem acesso a esta organização.")

    return organization


CurrentOrganizationDep = Annotated[CurrentOrganization, Depends(current_organization)]
