"""O registro de módulos: a lista do que a plataforma **sabe oferecer**.

Registro não é entitlement. Estar aqui significa que o código do módulo existe e a plataforma
pode vendê-lo; quem o enxerga é decidido por `module_entitlements`, tenant a tenant
(`entitlements.py`). Um módulo registrado nunca aparece pra um tenant sem entitlement."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from fastapi import APIRouter

from src.core.authz import Permission

type ModuleKey = str
"""A chave estável de um módulo — `refeicoes`, `frota`.

`snake_case`, porque vira segmento de rota (`/api/organizacoes/{orgId}/refeicoes/...`) e PK
lógica do entitlement. É `str` pelo mesmo motivo que `Permission` é: se o `core` guardasse o
enum, cada módulo novo o obrigaria a mudar, e a seta de dependência voltaria a apontar pra
fora."""

type ModulePersona = str
"""A persona que um módulo atende. `str` pelo mesmo motivo que `ModuleKey`: `Persona` é enum do
`access`, e o `core` não importa módulo."""


@dataclass(frozen=True, slots=True)
class ModuleNav:
    """Os metadados que a casca do frontend usa pra montar a navegação do módulo."""

    label: str
    path: str
    """Relativo à organização ativa — o frontend prefixa o `orgId`."""

    icon: str | None = None


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    """O que um módulo de negócio declara pra existir no superapp.

    É a peça 1 do contrato de plugagem; as outras são montar as rotas sob a chave (o que
    `mount_module` faz por ele), escopar dado por `organization_id`, checar as próprias
    permissões com `require_permission`, e não importar outro módulo de negócio."""

    key: ModuleKey
    name: str
    personas: Sequence[ModulePersona]
    permissions: Sequence[Permission]
    """As capabilities que o módulo declara. O kernel declara as *da plataforma*
    (`access/domain/permissions.py`); estas são as do módulo, e ninguém mais precisa
    conhecê-las."""

    nav: ModuleNav

    router: APIRouter | None = field(default=None, compare=False)
    """As rotas do módulo, que `mount_module` pendura sob a chave e atrás do
    `require_module`. `None` é módulo **só registrado**: a plataforma o oferece no catálogo e o
    entitlement dele já liga, mas ele ainda não tem endpoint — o caso de `refeicoes` e `frota`
    até as fases 2 e 3."""


_modules: dict[ModuleKey, ModuleDescriptor] = {}


def register_module(descriptor: ModuleDescriptor) -> None:
    """Põe um módulo no registro. Chamada na subida, via `mount_module`.

    Registrar duas vezes o mesmo descritor é inofensivo (a subida pode se repetir num
    processo); registrar **descritores diferentes** sob a mesma chave é erro de programação e
    estoura — a chave é a identidade do módulo em rota, entitlement e navegação."""

    registered = _modules.get(descriptor.key)
    if registered is not None and registered != descriptor:
        raise RuntimeError(
            f"Já existe um módulo registrado com a chave '{descriptor.key}'. "
            "A chave é a identidade do módulo — escolha outra."
        )

    _modules[descriptor.key] = descriptor


def registered_modules() -> tuple[ModuleDescriptor, ...]:
    """O catálogo: tudo que a plataforma sabe oferecer, ordenado por chave."""

    return tuple(_modules[key] for key in sorted(_modules))


def get_module(key: ModuleKey) -> ModuleDescriptor | None:
    """O descritor de uma chave, ou `None` se nada foi registrado com ela."""

    return _modules.get(key)


def is_registered(key: ModuleKey) -> bool:
    """Se a plataforma conhece esta chave. É o que separa "módulo que ninguém contratou" de
    "módulo que não existe" — o primeiro é 403, o segundo é 422 na hora de ligar."""

    return key in _modules
