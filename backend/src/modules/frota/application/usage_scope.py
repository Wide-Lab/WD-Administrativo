"""O que quem chama pode fazer com registro de uso.

Isto existe porque `frota.usages` tem **três** capabilities, não duas, e a do meio (`write_own`)
não é um subconjunto simples das outras: ela autoriza o mesmo verbo sobre um recorte de linhas.
Espalhar essa decisão pelos cinco use cases de uso faria cada um reinventar "e se for o próprio?"
— e o dia em que um deles esquecesse, o vazamento seria silencioso."""

import uuid
from dataclasses import dataclass

from src.core.authz import Permission
from src.core.exceptions import ForbiddenError, ValidationAppError
from src.modules.frota.application.ports.repositories import DriverRepositoryProtocol
from src.modules.frota.domain.permissions import FrotaPermissions

__all__ = ["UsageScope", "resolve_writable_driver_id"]


@dataclass(frozen=True, slots=True)
class UsageScope:
    """As três capabilities de uso, já resolvidas pra quem fez a requisição."""

    can_read_any: bool
    """`frota.usages.read` — vê os usos de toda a Empresa. Quem não a tem enxerga só os do
    próprio condutor; é o que faz `GET /usos` ser **uma** rota com escopo por dado, e não duas."""

    can_write_any: bool
    """`frota.usages.write` — lança, corrige e apaga uso de qualquer condutor."""

    can_write_own: bool
    """`frota.usages.write_own` — só onde o condutor é a própria pessoa. **Não** inclui apagar."""

    @classmethod
    def from_permissions(cls, granted: frozenset[Permission]) -> UsageScope:
        return cls(
            can_read_any=FrotaPermissions.USAGES_READ in granted,
            can_write_any=FrotaPermissions.USAGES_WRITE in granted,
            can_write_own=FrotaPermissions.USAGES_WRITE_OWN in granted,
        )

    @property
    def can_write_anything(self) -> bool:
        """Se a pessoa pode lançar **alguma** coisa. É o que o `POST /usos` e o `PATCH` exigem
        antes de perguntar *de quem* é o uso — quem não tem nenhuma das duas leva 403 sem o
        sistema precisar ir ao banco descobrir se ela é condutora."""

        return self.can_write_any or self.can_write_own


async def resolve_writable_driver_id(
    *,
    scope: UsageScope,
    drivers: DriverRepositoryProtocol,
    user_id: uuid.UUID,
    requested_driver_id: uuid.UUID | None,
) -> uuid.UUID:
    """De qual condutor este lançamento pode ser — o **único** lugar que decide isso.

    Quem tem `frota.usages.write` escolhe livremente. Quem tem só `write_own` age
    exclusivamente sobre o condutor vinculado ao próprio `user_id`: pedir outro é 403, e não ser
    condutor nenhum é 422 (a pessoa não está cadastrada como condutor, e a mensagem diz isso, em
    vez de um 403 que a faria procurar permissão que ela já tem).

    Omitir `requested_driver_id` significa "eu" — ver o docstring de `CreateUsageCommand`.

    Raises:
        ForbiddenError:
            Se quem só tem `write_own` pedir o condutor de outra pessoa.
        ValidationAppError:
            Se quem só tem `write_own` não tiver condutor vinculado, ou se quem pode tudo omitir
            o condutor sem ser condutor.
    """

    if scope.can_write_any and requested_driver_id is not None:
        return requested_driver_id

    own = await drivers.get_by_user_id(user_id)

    if own is None:
        raise ValidationAppError(
            "Você não está cadastrado como condutor nesta Empresa, então não pode lançar uma "
            "viagem em seu próprio nome. Peça ao gestor da frota para cadastrá-lo."
        )

    if requested_driver_id is None or requested_driver_id == own.id:
        return own.id

    raise ForbiddenError("Você só pode lançar viagens em seu próprio nome.")
