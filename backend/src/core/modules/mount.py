"""A linha única que pluga um app de negócio."""

from fastapi import APIRouter, Depends

from src.core.modules.entitlements import require_module
from src.core.modules.registry import ModuleDescriptor, register_module


def mount_module(api: APIRouter, descriptor: ModuleDescriptor) -> None:
    """Registra o módulo no catálogo e pendura as rotas dele sob a própria chave, atrás do
    `require_module`.

    É a **uma linha em `mount_routes`** que a spec 05 cobra, e ela faz do contrato de plugagem
    estrutura em vez de disciplina: o módulo não escolhe o prefixo nem lembra de aplicar o
    guard — sair de `/api/organizacoes/{orgId}/<chave>/*` ou responder sem entitlement exigiria
    ignorar este helper. Mesma divisão de trabalho do resto do projeto: onde dá pra impedir,
    impede-se; onde não dá, explica-se.

    Um descritor sem `router` só entra no catálogo: a plataforma passa a saber oferecê-lo (e o
    entitlement dele já liga) antes de ele ter endpoint. É o estado de `refeicoes` e `frota`
    até as fases 2 e 3.

    Args:
        api (APIRouter):
            O router `/api`.
        descriptor (ModuleDescriptor):
            O que o módulo declara — chave, personas, permissões, navegação e rotas.
    """

    register_module(descriptor)

    if descriptor.router is None:
        return

    api.include_router(
        descriptor.router,
        prefix=f"/organizacoes/{{orgId}}/{descriptor.key}",
        dependencies=[Depends(require_module(descriptor.key))],
    )
