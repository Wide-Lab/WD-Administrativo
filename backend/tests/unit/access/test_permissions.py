"""O mapa papel→permissão, sem banco.

`permissions.py` é `frozenset` e função pura: não precisa de Postgres e não deve pagar por um.
É o único lugar da suíte que roda em milissegundos, e é onde as decisões **contraintuitivas** do
mapa ficam presas — as que somem sozinhas quando alguém "arruma" o óbvio."""

import pytest

from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import Persona, Role
from src.modules.access.domain.permissions import (
    PERMISSIONS_BY_ROLE,
    PLATFORM_PERMISSIONS,
    ROLES_BY_ORGANIZATION_TYPE,
    is_role_valid_for,
    permissions_for,
    persona_for,
)


def test_todo_papel_vale_em_exatamente_um_tipo_de_organizacao() -> None:
    """Papel não vaza entre tipos: um `hr` não existe num Parceiro, e um `partner_admin` não
    existe numa Empresa. É este mapa que o `CHECK` de `memberships` gera — divergir aqui sem
    migration é o que o `--autogenerate` acusa."""

    vistos: list[Role] = []
    for roles in ROLES_BY_ORGANIZATION_TYPE.values():
        vistos.extend(roles)

    assert sorted(vistos) == sorted(Role)
    assert len(vistos) == len(set(vistos))


def test_todo_papel_tem_entrada_no_mapa_de_permissoes() -> None:
    """Um papel sem entrada seria `KeyError` em runtime, dentro de `require_permission` — 500
    onde deveria haver 403."""

    assert set(PERMISSIONS_BY_ROLE) == set(Role)


@pytest.mark.parametrize("organization_type", list(OrganizationType))
def test_todo_tipo_de_organizacao_tem_papeis(organization_type: OrganizationType) -> None:
    assert ROLES_BY_ORGANIZATION_TYPE[organization_type]


def test_hr_convida_mas_nao_edita_vinculo() -> None:
    """**A diferença entre `hr` e `company_admin` nesta fase, e ela é sutil de propósito.**

    Convidar é decidir quem entra; `members.write` é mexer em quem já entrou. Dar `members.write`
    ao `hr` "porque ele já convida" apagaria a distinção sem ninguém notar."""

    do_hr = permissions_for(Role.HR)

    assert PLATFORM_PERMISSIONS.INVITATIONS_WRITE in do_hr
    assert PLATFORM_PERMISSIONS.MEMBERS_READ in do_hr
    assert PLATFORM_PERMISSIONS.MEMBERS_WRITE not in do_hr


def test_platform_admin_nao_assina_convenio_no_lugar_do_cliente() -> None:
    """Contraintuitivo, e é o ponto: o instinto de quem refatora é "admin pode tudo".

    Conveniar é ato da Empresa, e o convênio carrega os termos *dela*. A plataforma provisiona
    tenants e conserta vínculos — não assina contrato por ninguém."""

    assert PLATFORM_PERMISSIONS.AGREEMENTS_WRITE not in permissions_for(Role.PLATFORM_ADMIN)
    assert PLATFORM_PERMISSIONS.AGREEMENTS_WRITE in permissions_for(Role.COMPANY_ADMIN)


def test_so_a_plataforma_vende_modulo() -> None:
    """O simétrico do teste acima: o cliente não se vende módulo sozinho. Um `company_admin` que
    pudesse ligar `refeicoes` tornaria o entitlement decorativo."""

    assert PLATFORM_PERMISSIONS.MODULES_WRITE in permissions_for(Role.PLATFORM_ADMIN)

    for role in Role:
        if role is not Role.PLATFORM_ADMIN:
            assert PLATFORM_PERMISSIONS.MODULES_WRITE not in permissions_for(role)


def test_papeis_sem_permissao_de_kernel_seguem_sem_ela() -> None:
    """`finance`, `manager` e `partner_operator` saem vazios, e isso é esperado, não esquecimento:
    o que eles fazem são capabilities de módulo de negócio, que a fase 2 declara. Eles existem
    porque o convite atribui papel e porque já mudam a persona."""

    assert permissions_for(Role.FINANCE) == frozenset()
    assert permissions_for(Role.MANAGER) == frozenset()
    assert permissions_for(Role.PARTNER_OPERATOR) == frozenset()


@pytest.mark.parametrize(
    ("organization_type", "role", "persona"),
    [
        (OrganizationType.PLATFORM, Role.PLATFORM_ADMIN, Persona.PLATFORM),
        (OrganizationType.COMPANY, Role.COMPANY_ADMIN, Persona.COMPANY_ADMIN),
        (OrganizationType.COMPANY, Role.HR, Persona.COMPANY_ADMIN),
        (OrganizationType.COMPANY, Role.FINANCE, Persona.COMPANY_ADMIN),
        (OrganizationType.COMPANY, Role.MANAGER, Persona.COMPANY_ADMIN),
        (OrganizationType.COMPANY, Role.COLLABORATOR, Persona.COLLABORATOR),
        (OrganizationType.PARTNER, Role.PARTNER_ADMIN, Persona.PARTNER),
        (OrganizationType.PARTNER, Role.PARTNER_OPERATOR, Persona.PARTNER),
    ],
)
def test_persona_sai_do_tipo_da_organizacao_mais_o_papel(
    organization_type: OrganizationType,
    role: Role,
    persona: Persona,
) -> None:
    """Numa Empresa a persona separa Admin de Colaborador; nos outros tipos o tipo já decide
    sozinho — todo membro de um Parceiro vê o portal do Parceiro. `hr`, `finance` e `manager`
    caírem na casca do Admin é decisão: o que os separa são permissões, não a casca."""

    assert persona_for(organization_type, role) is persona


def test_is_role_valid_for_responde_pelo_mapa() -> None:
    assert is_role_valid_for(OrganizationType.COMPANY, Role.HR)
    assert not is_role_valid_for(OrganizationType.PARTNER, Role.HR)
    assert not is_role_valid_for(OrganizationType.COMPANY, Role.PARTNER_ADMIN)
    assert not is_role_valid_for(OrganizationType.COMPANY, Role.PLATFORM_ADMIN)
