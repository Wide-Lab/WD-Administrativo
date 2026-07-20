"""O que só o `access` enxerga: que o papel de um `grants` existe, e que ele não é a Plataforma.

O `core` cobra o namespace (`tests/unit/core/test_module_registry.py`) porque é o que ele
consegue ver; `Role` é enum do `access`, então a validação de papel só pode morar aqui. As duas
falham **na subida** — um container que sobe com autorização errada é pior que um que não sobe."""

import pytest

from src.core.modules import ModuleDescriptor, ModuleNav, register_module
from src.modules.access.domain.entities import Role
from src.modules.access.domain.permissions import (
    module_permissions_for,
    permissions_for,
    validate_module_grants,
)


def _registrar(key: str, grants: dict[str, frozenset[str]]) -> ModuleDescriptor:
    descriptor = ModuleDescriptor(
        key=key,
        name=key.title(),
        personas=["company_admin"],
        grants=grants,
        nav=ModuleNav(label=key.title(), path=f"/{key}"),
    )
    register_module(descriptor)
    return descriptor


def test_grants_validos_passam_calados(registry_isolado: None) -> None:
    """Com todos os descritores válidos, `validate_module_grants` é no-op — inclusive com os
    `refeicoes` e `frota` reais, que declaram `grants={}`."""

    _registrar("smoke", {"manager": frozenset({"smoke.reports.read"})})

    validate_module_grants()


def test_papel_inexistente_derruba_a_subida(registry_isolado: None) -> None:
    """**O modo de falha que esta validação existe pra impedir.**

    `ModuleRole` é `str`, então `"colaborador"` (em português) não casa com papel nenhum e
    concederia silenciosamente **nada**: 403 em produção, e ninguém sabe por quê. O silêncio é a
    falha — por isso vira `RuntimeError` na subida, e não um log."""

    _registrar("smoke", {"colaborador": frozenset({"smoke.reports.read"})})

    with pytest.raises(RuntimeError, match="papéis que não existem"):
        validate_module_grants()


def test_modulo_nao_concede_a_platform_admin(registry_isolado: None) -> None:
    """**Contraintuitivo, e é por isso que está aqui: o instinto é "admin pode tudo".**

    `require_permission` afrouxa pra `platform_admin`; `require_module` não afrouxa pra ninguém.
    Se um módulo pudesse conceder à Plataforma, a assimetria quebraria por dentro: a organização
    `platform` não é `company` e a FK de `module_entitlements` a impede de contratar o módulo —
    seria uma permissão barrada pelo `require_module` que vem antes dela. Código morto que parece
    privilégio."""

    _registrar("smoke", {"platform_admin": frozenset({"smoke.reports.read"})})

    with pytest.raises(RuntimeError, match="não concede à Plataforma"):
        validate_module_grants()


def test_module_permissions_for_soma_os_descritores(registry_isolado: None) -> None:
    """A segunda fonte do `PermissionReader`: dois módulos concedendo ao mesmo papel se somam,
    e cada um só entrega o que declarou."""

    _registrar("smoke", {"manager": frozenset({"smoke.reports.read"})})
    _registrar("outro", {"manager": frozenset({"outro.trips.write"})})

    assert module_permissions_for(Role.MANAGER) == frozenset(
        {"smoke.reports.read", "outro.trips.write"}
    )
    assert module_permissions_for(Role.COLLABORATOR) == frozenset()


def test_capability_de_modulo_nao_entra_no_mapa_do_kernel(registry_isolado: None) -> None:
    """As duas fontes somam no reader, mas não se misturam: `PERMISSIONS_BY_ROLE` continua sendo
    só do kernel. Um módulo registrado não edita o mapa do `access` — é o que mantém a seta
    apontando pra dentro."""

    _registrar("smoke", {"manager": frozenset({"smoke.reports.read"})})

    assert permissions_for(Role.MANAGER) == frozenset()
