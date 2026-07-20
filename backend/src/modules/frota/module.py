"""O descritor da frota — o que o módulo declara pra existir no superapp.

**Este arquivo é o caminho de saída que `src/api/modules.py` anunciava desde a `05`**: um
descritor pertence ao módulo que ele descreve, e a frota agora existe. O placeholder de lá saiu;
`mount_routes` importa daqui.

O contrato de plugagem (spec 05) está cumprido inteiro, e três dos cinco itens sem esforço:
`mount_module` põe o prefixo e o `require_module`, e o `TenantScopedRepository` escopa o dado.
O que sobrou pro módulo foi declarar as capabilities (`grants`) e checá-las nas rotas com o mesmo
`require_permission` que o kernel usa."""

from src.core.modules import ModuleDescriptor, ModuleNav
from src.modules.frota.adapters.http.routes import router
from src.modules.frota.domain.permissions import GRANTS, MODULE_KEY

FROTA = ModuleDescriptor(
    key=MODULE_KEY,
    name="Frota",
    personas=["company_admin", "collaborator"],
    grants=GRANTS,
    nav=ModuleNav(label="Frota", path="/frota"),
    router=router,
)
"""O primeiro app de negócio do superapp.

`personas` não lista `partner`: frota é módulo de Empresa. O problema em aberto desde a `05` —
como um Parceiro alcança um módulo — **não** é resolvido nem esbarrado aqui; ele nasce com
Refeições.

`grants` mora em `domain/permissions.py` e não inline porque é regra de negócio, não configuração
de montagem: quem quiser saber por que o `manager` recebe tudo lê o domínio, não o descritor."""
