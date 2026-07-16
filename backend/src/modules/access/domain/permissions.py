"""Papéis, permissões e persona — o mapa fixo que o `access` é dono.

O kernel declara as permissões **da plataforma**; cada módulo de negócio declarará as suas
próprias (spec 05). O `core` não guarda catálogo nenhum: ele só sabe pedir uma `Permission`
a um `PermissionReader`."""

from collections.abc import Mapping

from src.core.authz import Permission
from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import Persona, Role

__all__ = [
    "PERMISSIONS_BY_ROLE",
    "PLATFORM_PERMISSIONS",
    "ROLES_BY_ORGANIZATION_TYPE",
    "is_role_valid_for",
    "permissions_for",
    "persona_for",
    "roles_for",
]


class PlatformPermissions:
    """As capabilities do kernel. Nomeadas `<recurso>.<ação>` — o recurso primeiro porque é
    ele que um módulo de negócio reconhece ao compor o guard."""

    ORGANIZATIONS_READ: Permission = "organizations.read"
    """Listar os tenants. Visão de plataforma, não de um tenant."""

    ORGANIZATIONS_WRITE: Permission = "organizations.write"
    """Provisionar um tenant (Empresa ou Parceiro)."""

    MEMBERS_READ: Permission = "members.read"
    """Listar os membros da organização ativa."""

    MEMBERS_WRITE: Permission = "members.write"
    """Mudar papel ou status de um membro da organização ativa."""

    AGREEMENTS_WRITE: Permission = "agreements.write"
    """Conveniar um Parceiro, suspender ou reativar o convênio. Só faz sentido numa Empresa —
    o `CreateAgreementUseCase` recusa os outros tipos."""


PLATFORM_PERMISSIONS = PlatformPermissions

ROLES_BY_ORGANIZATION_TYPE: Mapping[OrganizationType, frozenset[Role]] = {
    OrganizationType.PLATFORM: frozenset({Role.PLATFORM_ADMIN}),
    OrganizationType.COMPANY: frozenset(
        {
            Role.COMPANY_ADMIN,
            Role.HR,
            Role.FINANCE,
            Role.MANAGER,
            Role.COLLABORATOR,
        }
    ),
    OrganizationType.PARTNER: frozenset({Role.PARTNER_ADMIN, Role.PARTNER_OPERATOR}),
}
"""Papel só é válido no tipo de organização correspondente — um `hr` não existe num Parceiro.

Este mapa dá o 422 legível; quem **garante** é o `CHECK` de `memberships`, que enxerga o tipo
da organização pela FK composta. Mesma divisão de trabalho do convênio (spec 03): a aplicação
explica, o banco impede."""


PERMISSIONS_BY_ROLE: Mapping[Role, frozenset[Permission]] = {
    Role.PLATFORM_ADMIN: frozenset(
        {
            PlatformPermissions.ORGANIZATIONS_READ,
            PlatformPermissions.ORGANIZATIONS_WRITE,
            PlatformPermissions.MEMBERS_READ,
            PlatformPermissions.MEMBERS_WRITE,
        }
    ),
    Role.COMPANY_ADMIN: frozenset(
        {
            PlatformPermissions.MEMBERS_READ,
            PlatformPermissions.MEMBERS_WRITE,
            PlatformPermissions.AGREEMENTS_WRITE,
        }
    ),
    Role.HR: frozenset({PlatformPermissions.MEMBERS_READ}),
    Role.FINANCE: frozenset(),
    Role.MANAGER: frozenset(),
    Role.COLLABORATOR: frozenset(),
    Role.PARTNER_ADMIN: frozenset(
        {
            PlatformPermissions.MEMBERS_READ,
            PlatformPermissions.MEMBERS_WRITE,
        }
    ),
    Role.PARTNER_OPERATOR: frozenset(),
}
"""Papel → capabilities, fixo e em código.

`finance`, `manager` e `partner_operator` saem sem nenhuma permissão **de kernel** e isso é
esperado: o que esses papéis fazem (aprovar fatura, ler o catálogo) são capabilities de
módulo de negócio, que a spec 05 deixa cada módulo declarar. Eles existem aqui porque o papel
é o que o convite (spec 06) atribui, e porque já mudam a persona.

`platform_admin` não recebe `agreements.write`: conveniar é ato da Empresa, e o convênio
carrega os termos *dela*. A plataforma provisiona tenants e conserta vínculos — não assina
contrato no lugar do cliente."""


_PERSONA_BY_COMPANY_ROLE: Mapping[Role, Persona] = {
    Role.COMPANY_ADMIN: Persona.COMPANY_ADMIN,
    Role.HR: Persona.COMPANY_ADMIN,
    Role.FINANCE: Persona.COMPANY_ADMIN,
    Role.MANAGER: Persona.COMPANY_ADMIN,
    Role.COLLABORATOR: Persona.COLLABORATOR,
}


def roles_for(organization_type: OrganizationType) -> frozenset[Role]:
    """Os papéis que existem num tipo de organização."""

    return ROLES_BY_ORGANIZATION_TYPE[organization_type]


def is_role_valid_for(organization_type: OrganizationType, role: Role) -> bool:
    """Se `role` faz sentido numa organização de `organization_type`."""

    return role in ROLES_BY_ORGANIZATION_TYPE[organization_type]


def permissions_for(role: Role) -> frozenset[Permission]:
    """As capabilities de kernel de um papel."""

    return PERMISSIONS_BY_ROLE[role]


def persona_for(organization_type: OrganizationType, role: Role) -> Persona:
    """A superfície de frontend de um vínculo.

    Numa `company` a persona separa Admin de Colaborador; nos outros tipos o tipo da
    organização já decide sozinho — todo membro de um Parceiro vê o portal do Parceiro."""

    match organization_type:
        case OrganizationType.PLATFORM:
            return Persona.PLATFORM
        case OrganizationType.PARTNER:
            return Persona.PARTNER
        case OrganizationType.COMPANY:
            return _PERSONA_BY_COMPANY_ROLE[role]
