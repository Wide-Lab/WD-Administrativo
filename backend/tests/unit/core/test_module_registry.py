"""O descritor e a regra de namespace, sem banco e sem app.

`register_module` é a fronteira onde o `core` impede o que **consegue** enxergar: que um módulo
conceda capability fora do próprio espaço de nomes. Quem é dono de `Role` é o `access`, e a
validação de papel mora lá (`test_permissions.py`) — a divisão é a mesma do resto do projeto."""

import pytest

from src.core.modules import ModuleDescriptor, ModuleNav, register_module, registered_modules


def _descritor(
    key: str = "smoke",
    grants: dict[str, frozenset[str]] | None = None,
) -> ModuleDescriptor:
    return ModuleDescriptor(
        key=key,
        name="Smoke",
        personas=["company_admin"],
        grants=grants if grants is not None else {},
        nav=ModuleNav(label="Smoke", path="/smoke"),
    )


def test_permissions_deriva_o_catalogo_dos_grants() -> None:
    """A lista plana da spec 05 não sumiu — virou propriedade. `grants` diz quem recebe;
    `permissions` responde "o que este módulo declara", que é a pergunta do catálogo."""

    descritor = _descritor(
        grants={
            "manager": frozenset({"smoke.reports.read"}),
            "collaborator": frozenset({"smoke.reports.read", "smoke.trips.write"}),
        }
    )

    assert descritor.permissions == frozenset({"smoke.reports.read", "smoke.trips.write"})


def test_permissions_de_modulo_sem_grants_e_vazio() -> None:
    """O caso de `refeicoes` e `frota` até as fases 2 e 3 — e o `union(*())` que ele exercita
    estoura se escrito ingenuamente."""

    assert _descritor().permissions == frozenset()


def test_permission_monta_a_capability_com_o_prefixo() -> None:
    """O helper existe pra ninguém repetir a chave à mão e cair na regra de namespace."""

    assert _descritor(key="frota").permission("vehicles.write") == "frota.vehicles.write"


def test_modulo_nao_registra_capability_fora_do_proprio_namespace(
    registry_isolado: None,
) -> None:
    """**O teste que impede escalada de privilégio.**

    Sem a regra, um módulo declara `grants={"collaborator": {"organizations.write"}}` e um
    Colaborador qualquer passa a provisionar tenant — porque o mecanismo *soma* as concessões do
    módulo ao mapa do kernel. Com ela, o espaço de nomes do kernel é inalcançável por construção,
    e a app **não sobe**: erro de subida é melhor que privilégio silencioso."""

    escalada = _descritor(grants={"collaborator": frozenset({"organizations.write"})})

    with pytest.raises(RuntimeError, match="fora do próprio namespace"):
        register_module(escalada)

    assert escalada not in registered_modules()


def test_modulo_nao_registra_capability_sem_prefixo(registry_isolado: None) -> None:
    """O caso menos malicioso e mais provável: `reports.read` em vez de `smoke.reports.read`.

    É o que causaria colisão entre módulos — Frota e Refeições vão os dois querer `reports.read`,
    e sem prefixo quem registrasse por último venceria."""

    sem_prefixo = _descritor(grants={"manager": frozenset({"reports.read"})})

    with pytest.raises(RuntimeError, match="fora do próprio namespace"):
        register_module(sem_prefixo)


def test_modulo_com_grants_namespaced_registra(registry_isolado: None) -> None:
    """O par dos dois acima: sem ele, o `RuntimeError` poderia estar vindo de qualquer coisa."""

    valido = _descritor(grants={"manager": frozenset({"smoke.reports.read"})})

    register_module(valido)

    assert valido in registered_modules()
