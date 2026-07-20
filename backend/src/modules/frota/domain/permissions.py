"""As capabilities da frota e quem as recebe — o `grants` do descritor.

**Este arquivo é a estreia do mecanismo da `backend/09`.** Nada aqui toca
`PERMISSIONS_BY_ROLE`, que é do `access`: o descritor declara papel→capabilities, o
`SqlAlchemyMembershipReader` soma os módulos registrados ao mapa do kernel, e um
`require_permission("frota.vehicles.write")` numa rota daqui chega ao papel certo **sem uma
linha no `access` e sem tocar `core`**.

Os papéis são `str` e não `Role` pelo mesmo motivo que `ModuleRole` é `str` no `core`: `Role` é
enum do `access`, e módulo não importa módulo. Quem cobra o preço disso (um typo concederia
silenciosamente nada) é `validate_module_grants()`, na subida."""

from collections.abc import Mapping

from src.core.authz import Permission
from src.core.modules import ModuleRole

__all__ = [
    "GRANTS",
    "MODULE_KEY",
    "FrotaPermissions",
]

MODULE_KEY = "frota"
"""A chave do módulo. Mora aqui, e não só no descritor, porque é ela que forma o namespace de
toda capability abaixo — e `register_module` recusa a subida de quem sair dele."""


class FrotaPermissions:
    """As capabilities que a frota declara.

    Todas prefixadas por `frota.`, e não por disciplina: `register_module` levanta
    `RuntimeError` se uma escapar do namespace. A regra existe pra que um módulo não consiga
    conceder permissão de kernel (`organizations.write`) nem colidir com outro módulo que também
    queira `reports.read`."""

    VEHICLES_READ: Permission = f"{MODULE_KEY}.vehicles.read"
    """Ver a lista de veículos."""

    VEHICLES_WRITE: Permission = f"{MODULE_KEY}.vehicles.write"
    """Cadastrar e editar veículo."""

    DRIVERS_READ: Permission = f"{MODULE_KEY}.drivers.read"
    """Ver a lista de condutores."""

    DRIVERS_WRITE: Permission = f"{MODULE_KEY}.drivers.write"
    """Cadastrar e editar condutor."""

    USAGES_READ: Permission = f"{MODULE_KEY}.usages.read"
    """Ver **todos** os registros de uso da Empresa. É também o que decide o escopo do
    `GET /usos`: quem não a tem enxerga só os do próprio condutor."""

    USAGES_WRITE: Permission = f"{MODULE_KEY}.usages.write"
    """Lançar, corrigir e apagar uso de **qualquer** condutor."""

    USAGES_WRITE_OWN: Permission = f"{MODULE_KEY}.usages.write_own"
    """Lançar e encerrar uso em que o condutor é **você** — o vínculo `drivers.user_id`.

    **Não** inclui apagar: o registro é a matéria-prima do relatório, e quem apaga a própria
    viagem apaga a evidência. Corrigir, sim (`PATCH`); sumir, é ato do gestor."""


_ALL: frozenset[Permission] = frozenset(
    {
        FrotaPermissions.VEHICLES_READ,
        FrotaPermissions.VEHICLES_WRITE,
        FrotaPermissions.DRIVERS_READ,
        FrotaPermissions.DRIVERS_WRITE,
        FrotaPermissions.USAGES_READ,
        FrotaPermissions.USAGES_WRITE,
        FrotaPermissions.USAGES_WRITE_OWN,
    }
)


GRANTS: Mapping[ModuleRole, frozenset[Permission]] = {
    "company_admin": _ALL,
    "manager": _ALL,
    "collaborator": frozenset(
        {
            FrotaPermissions.VEHICLES_READ,
            FrotaPermissions.USAGES_WRITE_OWN,
        }
    ),
}
"""Papel → o que a frota lhe concede.

`manager` recebe tudo porque **é ele o gestor de frota** — e é aqui que o papel finalmente ganha
capability. A `04` o deixou com `frozenset()` dizendo que o que ele faz são capabilities de
módulo; esta é a primeira spec a cumprir a promessa.

`collaborator` recebe `vehicles.read` porque **precisa escolher o carro** pra lançar a viagem —
sem isso o formulário não tem o que oferecer. Não recebe `drivers.read`: ele lança em nome de si
mesmo, e a lista de condutores da Empresa não é dele.

`hr` e `finance` **não aparecem**, e a ausência é a decisão: RH cuida de gente, e o custo da
frota está fora de escopo — quando entrar, `finance` ganha leitura. Ausente e não
`frozenset()` vazio porque `module_permissions_for` já resolve a falta com
`grants.get(role, frozenset())`, e uma linha vazia sugeriria que alguém pensou em dar algo.

`platform_admin` não está aqui e **não pode estar**: `validate_module_grants()` derruba a subida
de quem conceder à Plataforma. A organização `platform` não é `company` e não consegue nem
contratar o módulo — seria permissão barrada pelo `require_module` que vem antes dela. A Widelab
vende módulo; ela não opera a frota do cliente."""
