"""O registro de módulos: a lista do que a plataforma **sabe oferecer**.

Registro não é entitlement. Estar aqui significa que o código do módulo existe e a plataforma
pode vendê-lo; quem o enxerga é decidido por `module_entitlements`, tenant a tenant
(`entitlements.py`). Um módulo registrado nunca aparece pra um tenant sem entitlement."""

from collections.abc import Mapping, Sequence
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

type ModuleRole = str
"""O papel a que o módulo concede uma capability. `str` pelo mesmo motivo que `ModulePersona`:
`Role` é enum do `access`, e o `core` não importa módulo.

O preço é que um papel inexistente (`"colaborador"`, em português, ou com typo) não casaria com
papel nenhum e concederia silenciosamente **nada** — 403 em produção sem ninguém saber por quê.
Quem cobra esse preço na subida é `validate_module_grants()`, do `access`, que é o dono de
`Role`. Divisão de trabalho de sempre: o `core` impede o que enxerga (o namespace, logo abaixo),
o `access` impede o que só ele enxerga (o papel)."""


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

    grants: Mapping[ModuleRole, frozenset[Permission]]
    """Papel → as capabilities que este módulo lhe concede.

    É **concessão**, não catálogo: o `PermissionReader` do `access` soma isto ao mapa do kernel
    (`PERMISSIONS_BY_ROLE`), e é o que faz um `require_permission("frota.vehicles.write")` numa
    rota de módulo chegar a um papel sem nenhuma linha no `access`. Um mapa vazio é módulo que
    ainda não declara nada.

    Chamava-se `permissions` e era uma lista plana (spec 05), que não ligava em nada. O nome
    mudou junto com o significado de propósito: manter `permissions` com semântica nova faria
    toda leitura de código da 05 mentir. O catálogo plano continua disponível, derivado, na
    propriedade `permissions` abaixo.

    Toda capability aqui tem que começar com `<chave>.` — ver `register_module`."""

    nav: ModuleNav

    router: APIRouter | None = field(default=None, compare=False)
    """As rotas do módulo, que `mount_module` pendura sob a chave e atrás do
    `require_module`. `None` é módulo **só registrado**: a plataforma o oferece no catálogo e o
    entitlement dele já liga, mas ele ainda não tem endpoint — o caso de `refeicoes` e `frota`
    até as fases 2 e 3."""

    @property
    def permissions(self) -> frozenset[Permission]:
        """O catálogo: toda capability que este módulo declara, sem quem a recebe."""

        return frozenset().union(*self.grants.values()) if self.grants else frozenset()

    def permission(self, suffix: str) -> Permission:
        """`FROTA.permission("vehicles.write")` → `"frota.vehicles.write"`.

        Existe pra ninguém precisar repetir a chave à mão e errar o namespace que
        `register_module` cobra."""

        return f"{self.key}.{suffix}"


_modules: dict[ModuleKey, ModuleDescriptor] = {}


def _assert_grants_are_namespaced(descriptor: ModuleDescriptor) -> None:
    """Toda capability de `grants` começa com `<chave>.`, ou o módulo não sobe.

    Uma regra, três problemas:

    1. **Escalada de privilégio.** O mecanismo desta camada *soma* as concessões do módulo ao
       mapa do kernel. Sem a regra, um descritor com `grants={"collaborator":
       {"organizations.write"}}` daria a um Colaborador qualquer o poder de provisionar tenant —
       por malícia ou por copiar-colar. Com ela o espaço de nomes do kernel é inalcançável **por
       construção**: `organizations.write` não começa com `frota.`.
    2. **Colisão entre módulos.** Frota e Refeições vão os dois querer `reports.read`. Sem
       prefixo, quem registrasse por último venceria, e um `manager` de frota ganharia relatório
       de refeições de brinde.
    3. **Legibilidade no ponto de uso.** `require_permission("frota.vehicles.write")` diz de quem
       é a regra sem abrir o descritor.

    Mora aqui, e não em `mount_module`, porque **registrar** é o ato que põe o descritor no mapa
    que o `PermissionReader` vai somar: é neste ponto que a invariante tem que valer, inclusive
    pra quem chame `register_module` direto."""

    prefixo = f"{descriptor.key}."
    fora = sorted(
        permission
        for permissions in descriptor.grants.values()
        for permission in permissions
        if not permission.startswith(prefixo)
    )
    if fora:
        raise RuntimeError(
            f"O módulo '{descriptor.key}' concede capabilities fora do próprio namespace: "
            f"{', '.join(fora)}. Toda capability de um módulo começa com '{prefixo}' — "
            f"use {descriptor.key.upper()}.permission('...') pra montá-la. Sem isso, um módulo "
            "poderia conceder permissão de kernel (escalada de privilégio) ou colidir com outro."
        )


def register_module(descriptor: ModuleDescriptor) -> None:
    """Põe um módulo no registro. Chamada na subida, via `mount_module`.

    Registrar duas vezes o mesmo descritor é inofensivo (a subida pode se repetir num
    processo); registrar **descritores diferentes** sob a mesma chave é erro de programação e
    estoura — a chave é a identidade do módulo em rota, entitlement e navegação.

    Recusa também quem declara `grants` fora do próprio namespace: a app não sobe. Um container
    que sobe com autorização errada é pior do que um container que não sobe."""

    _assert_grants_are_namespaced(descriptor)

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
