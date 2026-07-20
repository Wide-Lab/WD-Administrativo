"""Papéis, permissões e persona — o mapa fixo que o `access` é dono.

O kernel declara as permissões **da plataforma**; cada módulo de negócio declarará as suas
próprias (spec 05). O `core` não guarda catálogo nenhum: ele só sabe pedir uma `Permission`
a um `PermissionReader`."""

from collections.abc import Mapping

from src.core.authz import Permission
from src.core.modules import registered_modules
from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import Persona, Role

__all__ = [
    "PERMISSIONS_BY_ROLE",
    "PLATFORM_PERMISSIONS",
    "ROLES_BY_ORGANIZATION_TYPE",
    "is_role_valid_for",
    "module_permissions_for",
    "permissions_for",
    "persona_for",
    "roles_for",
    "validate_module_grants",
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

    INVITATIONS_WRITE: Permission = "invitations.write"
    """Convidar alguém pra organização ativa, com um papel já definido.

    É `members.write` de uma pessoa que ainda não é membro — e não se confunde com ele: quem
    edita vínculo existente mexe em quem já entrou, quem convida decide quem entra. O `hr`
    tem esta e **não** tem `members.write`, e é exatamente essa a diferença entre os dois
    papéis nesta fase."""

    MODULES_READ: Permission = "modules.read"
    """Ver o que a Empresa ativa contratou, junto do catálogo do que dá pra contratar."""

    MODULES_WRITE: Permission = "modules.write"
    """Habilitar ou desabilitar um módulo na Empresa ativa — vender, na prática.

    Só a Plataforma a tem, e é o simétrico do `agreements.write`: lá, a Widelab não assina
    contrato no lugar do cliente; aqui, o cliente não se vende módulo sozinho. Um
    `company_admin` que pudesse ligar `refeicoes` tornaria o entitlement decorativo."""


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
            PlatformPermissions.MODULES_READ,
            PlatformPermissions.MODULES_WRITE,
        }
    ),
    Role.COMPANY_ADMIN: frozenset(
        {
            PlatformPermissions.MEMBERS_READ,
            PlatformPermissions.MEMBERS_WRITE,
            PlatformPermissions.AGREEMENTS_WRITE,
            PlatformPermissions.INVITATIONS_WRITE,
        }
    ),
    Role.HR: frozenset(
        {
            PlatformPermissions.MEMBERS_READ,
            PlatformPermissions.INVITATIONS_WRITE,
        }
    ),
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


def module_permissions_for(role: Role) -> frozenset[Permission]:
    """As capabilities que os **módulos registrados** concedem a um papel.

    A segunda fonte do `SqlAlchemyMembershipReader`, ao lado de `permissions_for`. É o que faz um
    app de negócio autorizar as próprias rotas com o mesmo `require_permission(...)` do kernel,
    sem uma linha aqui e sem tocar o `core`.

    **O `access` importar `src.core.modules` é legal e não é exceção:** módulo importa `core` à
    vontade; o proibido é o contrário, e módulo importar módulo. A seta segue apontando pra
    dentro — o `core` continua sem saber que papel existe, e a Frota continua sem saber que o
    `access` existe.

    Note que isto **não** é chamado pra parcela de plataforma: ver `validate_module_grants`."""

    return frozenset().union(
        *(descriptor.grants.get(role.value, frozenset()) for descriptor in registered_modules())
    )


def validate_module_grants() -> None:
    """Confere os `grants` de todo módulo registrado. Chamada uma vez no fim de `mount_routes`,
    depois de todos os `mount_module`.

    Existe porque `ModuleRole` é `str`: um `grants={"colaborador": ...}` (em português, ou com
    typo) não casaria com papel nenhum e concederia silenciosamente **nada** — o pior modo de
    falha possível, 403 em produção sem ninguém saber por quê. O `core` não tem como pegar isso;
    quem é dono de `Role` é o `access`, e é aqui que o preço é pago **na subida**.

    Não é uma quinta porta no `mount_routes`: é verificação, não registro de um `Reader`. O teto
    de quatro portas que a spec 05 declarou segue de pé.

    Raises:
        RuntimeError:
            Se um módulo concede a um papel que não existe, ou a `platform_admin`.
    """

    papeis_validos = {role.value for role in Role}

    for descriptor in registered_modules():
        desconhecidos = sorted(set(descriptor.grants) - papeis_validos)
        if desconhecidos:
            raise RuntimeError(
                f"O módulo '{descriptor.key}' concede a papéis que não existem: "
                f"{', '.join(desconhecidos)}. Os papéis são {', '.join(sorted(papeis_validos))} — "
                "um nome que não casa concederia nada, em silêncio."
            )

        if Role.PLATFORM_ADMIN.value in descriptor.grants:
            raise RuntimeError(
                f"O módulo '{descriptor.key}' concede a '{Role.PLATFORM_ADMIN.value}', e módulo "
                "não concede à Plataforma. `require_module` não afrouxa pra ninguém, e a "
                "organização `platform` não é `company` — ela não pode nem contratar o módulo. "
                "Seria uma permissão barrada pelo `require_module` que vem antes dela: código "
                "morto que parece privilégio. A Widelab vende módulo; ela não opera a frota do "
                "cliente."
            )


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
