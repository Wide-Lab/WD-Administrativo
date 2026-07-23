from src.core.exceptions import PersistenceError
from src.core.pagination.params import Page, PageParams
from src.core.security import UserReader
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.dtos.filters import MembershipFilters
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import MembershipWithUser


class ListMembersUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol, users: UserReader) -> None:
        """
        Inicializa o use case de listagem de membros.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
            users (UserReader):
                A porta de identidade do `core` — quem traduz `user_id` em nome e e-mail. Vem
                por injeção como o repositório: `application` não conhece adapter, e muito
                menos o módulo `auth`, dono da tabela `users`.
        """

        self._uow = uow
        self._users = users

    async def execute(
        self,
        organization: CurrentOrganization,
        page_params: PageParams,
    ) -> Page[MembershipWithUser]:
        """
        Lista os membros da organização do path, cada um já com a pessoa do outro lado.

        Escopado pela organização ativa e não por quem pergunta: o filtro por
        `organization.id` é o que impede um admin de uma Empresa de enxergar o quadro de
        outra. Inclui os vínculos desativados — quem administra membros precisa ver quem foi
        desligado pra poder reativar.

        A identidade entra **aqui**, e não no repositório: `memberships` é do `access` e `users`
        é do `auth`, então o join não existe em SQL nenhum desta aplicação. São duas consultas
        por página — a dos vínculos e uma só pelos perfis de todos eles —, e o custo é o preço
        do seam de extração. A alternativa era a tela mostrar UUID, que foi o que ela mostrou
        até aqui.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            page_params (PageParams):
                Paginação.

        Returns:
            Page[MembershipWithUser]:
                Os vínculos da organização, com nome e e-mail de cada pessoa.

        Raises:
            PersistenceError:
                Se um vínculo apontar pra um usuário que não existe.
        """

        async with self._uow as uow:
            page = await uow.memberships.paginate(
                page_params=page_params,
                filters=MembershipFilters(organization_id=organization.id),
            )

            # Dentro do contexto de propósito: o reader recebe a **mesma sessão** da unit of
            # work (é a `SessionDep` da requisição), e o `__aexit__` dela fecha essa sessão.
            # Perguntar depois de sair abriria uma segunda transação pra ler o que a primeira
            # acabou de referenciar.
            profiles = await self._users.list_profiles_by_ids([item.user_id for item in page.items])

        # Inalcançável enquanto a FK `fk_memberships_user` estiver de pé — ela vive só na
        # migration, porque declará-la no model faria módulo importar módulo, e é justamente por
        # isso que o caso é checado aqui: a garantia está num lugar que este arquivo não enxerga.
        # Um `KeyError` cru daria 500 sem dizer o que quebrou.
        faltando = sorted(str(item.user_id) for item in page.items if item.user_id not in profiles)
        if faltando:
            raise PersistenceError(
                f"Vínculos apontam para usuários que não existem: {', '.join(faltando)}."
            )

        return Page(
            items=[
                MembershipWithUser(membership=item, user=profiles[item.user_id])
                for item in page.items
            ],
            total=page.total,
            page=page.page,
            page_size=page.page_size,
        )
