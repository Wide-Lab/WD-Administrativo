import uuid

from src.core.exceptions import NotFoundError, PersistenceError, ValidationAppError
from src.core.security import CurrentUser, UserReader
from src.core.tenancy import CurrentOrganization
from src.core.types import UNSET
from src.modules.access.application.dtos.commands import UpdateMembershipCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import MembershipWithUser, UpdateMembership
from src.modules.access.domain.permissions import is_role_valid_for, roles_for


class UpdateMembershipUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol, users: UserReader) -> None:
        """
        Inicializa o use case de mudança de papel/status de um membro.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
            users (UserReader):
                A porta de identidade do `core`, pela mesma razão do `ListMembersUseCase`: a
                resposta desta rota é um membro, e um membro agora tem nome e e-mail. Devolver
                aqui um formato mais pobre que o da listagem faria a tela reparsear duas formas
                do mesmo objeto.
        """

        self._uow = uow
        self._users = users

    async def execute(
        self,
        organization: CurrentOrganization,
        membership_id: uuid.UUID,
        command: UpdateMembershipCommand,
        actor: CurrentUser,
    ) -> MembershipWithUser:
        """
        Muda o papel e/ou o status de um vínculo da organização do path.

        ## Ninguém edita o próprio vínculo

        Papel e status do vínculo de quem pede respondem 422, e **não** é uma cortesia da tela
        elevada a regra: `members.write` só existe em `company_admin`, `partner_admin` e
        `platform_admin`, então toda mudança que alguém faria na própria linha é um
        rebaixamento — ou uma desativação, que é o mesmo estrago pela porta ao lado. Sem esta
        trava, um `company_admin` se rebaixava a `collaborator` e a organização ficava sem
        quem a administre, sem erro nenhum e sem caminho de volta que não fosse a Widelab ou a
        CLI.

        A trava vale por tabela, e é isso que a torna barata: como ninguém tira a si mesmo, e
        cada um só edita os outros, **sempre sobra pelo menos um administrador** — a regra do
        "último admin ativo" não precisa existir como consulta separada. O caso extremo (uma
        organização que trave por outro caminho) segue coberto pelo `platform_admin`, que
        alcança qualquer tenant.

        E ela mora aqui, e não na tela: um `if` no frontend seria um cadeado pintado, que some
        no primeiro `curl` e faz todo mundo achar que o caso está tratado.

        ## O resto

        A conferência de papel×tipo aqui existe pra devolver 422 legível, **não** pra garantir
        a integridade: quem garante é o `CHECK` de `memberships`, ancorado pela FK composta
        contra `organizations(id, type)` — um `UPDATE` que passe por fora desta aplicação
        falha do mesmo jeito. Mesma divisão de trabalho do convênio (spec 03).

        Um vínculo de outra organização responde 404, não 403 — quem não pode vê-lo também não
        deveria descobrir que ele existe. Mesma escolha do `PATCH /convenios/{id}`.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            membership_id (uuid.UUID):
                O vínculo a atualizar.
            command (UpdateMembershipCommand):
                O novo papel e/ou status.
            actor (CurrentUser):
                Quem está pedindo a mudança — é a comparação com ele que barra a auto-edição.

        Returns:
            MembershipWithUser:
                O vínculo atualizado, com a pessoa do outro lado.

        Raises:
            NotFoundError:
                Se o vínculo não existir ou não pertencer à organização ativa.
            ValidationAppError:
                Se o vínculo for o de quem pede, se o papel não existir no tipo desta
                organização, ou se o corpo não pedir mudança nenhuma.
            PersistenceError:
                Se o vínculo apontar pra um usuário que não existe.
        """

        if command.role is None and command.status is None:
            raise ValidationAppError("Informe ao menos um campo para atualizar.")

        if command.role is not None and not is_role_valid_for(organization.type, command.role):
            valid = ", ".join(sorted(role.value for role in roles_for(organization.type)))
            raise ValidationAppError(
                f"O papel '{command.role.value}' não existe numa organização do tipo "
                f"'{organization.type.value}'. Papéis válidos: {valid}."
            )

        async with self._uow as uow:
            membership = await uow.memberships.get_by_id_or_none(membership_id)
            if membership is None or membership.organization_id != organization.id:
                raise NotFoundError("Vínculo não encontrado.")

            # Depois do 404, e não antes: quem não pode ver o vínculo não descobre nada por
            # aqui. Antes do `update`, porque a transação não chega a abrir.
            if membership.user_id == actor.id:
                raise ValidationAppError(
                    "Você não pode alterar o seu próprio vínculo com esta organização. Mudar o "
                    "próprio papel ou desativá-lo tiraria de você o acesso que administra esta "
                    "organização — inclusive o de desfazer a mudança. Peça a outro "
                    "administrador, ou à Widelab."
                )

            updated = await uow.memberships.update(
                membership_id,
                UpdateMembership(
                    role=command.role if command.role is not None else UNSET,
                    status=command.status if command.status is not None else UNSET,
                ),
            )
            await uow.commit()

            profiles = await self._users.list_profiles_by_ids([updated.user_id])
            profile = profiles.get(updated.user_id)
            if profile is None:
                raise PersistenceError(
                    f"O vínculo aponta para um usuário que não existe: {updated.user_id}."
                )

            return MembershipWithUser(membership=updated, user=profile)
