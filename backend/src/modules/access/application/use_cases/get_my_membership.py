from dataclasses import dataclass

from src.core.authz import Permission
from src.core.exceptions import ForbiddenError
from src.core.security import UserId
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import Persona, Role
from src.modules.access.domain.permissions import permissions_for, persona_for


@dataclass(frozen=True, slots=True)
class MyMembership:
    """Minha situação **nesta** organização: o que a casca do frontend usa pra montar
    navegação e liberar ações."""

    role: Role
    persona: Persona
    permissions: frozenset[Permission]


class GetMyMembershipUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de "eu nesta organização".

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(self, user_id: UserId, organization: CurrentOrganization) -> MyMembership:
        """
        Resolve papel, persona e permissões de uma pessoa numa organização.

        Não há "organização ativa" no servidor nem default a adivinhar: qual organização é
        sempre o `orgId` do path, e é isso que faz o mesmo login devolver personas diferentes
        em `orgId` diferentes, sem novo login.

        O `platform_admin` é o caso sem vínculo local: ele alcança qualquer tenant sem ter
        linha em `memberships` daquela Empresa. Aqui ele se apresenta pelo que é — papel
        `platform_admin`, persona `platform` —, em vez de virar um membro fantasma da Empresa.

        Args:
            user_id (UserId):
                Quem fez a requisição.
            organization (CurrentOrganization):
                A organização do path, já validada por `current_organization`.

        Returns:
            MyMembership:
                Papel, persona e permissões nesta organização.

        Raises:
            ForbiddenError:
                Se não houver vínculo nem `platform_admin`. Inalcançável via HTTP —
                `current_organization` já teria negado —, mas o use case não se apoia num
                invariante que vive noutra camada pra decidir quem é `platform_admin`.
        """

        async with self._uow as uow:
            membership = await uow.memberships.get_active_for_user_and_organization(
                user_id=user_id,
                organization_id=organization.id,
            )
            if membership is not None:
                return MyMembership(
                    role=membership.role,
                    persona=persona_for(organization.type, membership.role),
                    permissions=permissions_for(membership.role),
                )

            if await uow.memberships.is_platform_admin(user_id):
                return MyMembership(
                    role=Role.PLATFORM_ADMIN,
                    persona=Persona.PLATFORM,
                    permissions=permissions_for(Role.PLATFORM_ADMIN),
                )

            raise ForbiddenError("Você não tem vínculo com esta organização.")
