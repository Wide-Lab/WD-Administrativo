from src.core.security import UserId
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import MembershipWithOrganization


class GetMyContextUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de contexto global.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(self, user_id: UserId) -> list[MembershipWithOrganization]:
        """
        Lista os vínculos ativos de uma pessoa — o "bootstrap" de roteamento e do seletor de
        organização do frontend.

        É o único ponto do sistema que enxerga **através** das organizações, e é por isso que
        não é escopado por tenant: a pergunta aqui é justamente "onde eu entro?", que precede
        a escolha do `orgId`. Papel e permissões *dentro* de uma organização vêm do
        `GET /api/organizacoes/{orgId}/me`.

        Args:
            user_id (UserId):
                Quem fez a requisição.

        Returns:
            list[MembershipWithOrganization]:
                Os vínculos ativos, cada um com a sua organização. Vazio é resposta legítima —
                um usuário recém-criado pelo CLI ainda não tem vínculo.
        """

        async with self._uow as uow:
            return await uow.memberships.list_active_for_user(user_id)
