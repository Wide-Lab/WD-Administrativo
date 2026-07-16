from src.core.exceptions import ConflictError
from src.core.security import UserDirectory, UserId
from src.core.tenancy import OrganizationType
from src.modules.access.application.dtos.commands import RegisterPartnerCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import NewMembership, NewOrganization, Role


class RegisterPartnerUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol, directory: UserDirectory) -> None:
        """
        Inicializa o use case de auto-cadastro de Parceiro.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
            directory (UserDirectory):
                Porta de identidade — o `access` cria o admin sem importar `auth`.
        """

        self._uow = uow
        self._directory = directory

    async def execute(self, command: RegisterPartnerCommand) -> UserId:
        """
        Cadastra um Parceiro: a organização, o primeiro `partner_admin` e o vínculo entre os
        dois, numa transação só.

        **É rota pública, e é a única que cria organização sem `platform_admin`** — de
        propósito: o Parceiro é organização de primeiro nível e se cadastra uma vez, sozinho;
        quem o liga a cada Empresa depois é o convênio (spec 03), que continua sendo ato da
        Empresa. Cadastrar-se aqui não dá acesso a tenant nenhum: até existir convênio, o
        Parceiro só enxerga a si mesmo.

        A atomicidade não vem de um `try`: vem de `organizations`, `users` e `memberships`
        compartilharem a sessão da requisição — a porta `UserDirectory` recebe a mesma
        `SessionDep` da uow. Um `commit` cobre os três, e o e-mail duplicado que estoura no
        `flush` do `create` desfaz a organização junto. Sem organização órfã, que é o critério
        3 da spec.

        Args:
            command (RegisterPartnerCommand):
                Nome e documento do Parceiro, mais nome/e-mail/senha do admin.

        Returns:
            UserId:
                O admin recém-criado — é para ele que a rota emite a sessão.

        Raises:
            ConflictError:
                Se já existir conta com o e-mail informado.
        """

        async with self._uow as uow:
            # A checagem antes do `create` existe pro 409 legível no caso comum; quem
            # **garante** é o único de `users.email`, que o `SqlAlchemyUserDirectory` traduz.
            # Sem ela, a corrida entre dois cadastros simultâneos daria o mesmo 409 — com ela,
            # o caso normal não depende de exceção.
            if await self._directory.find_id_by_email(command.admin_email) is not None:
                raise ConflictError("Já existe uma conta com este e-mail.")

            organization = await uow.organizations.create(
                NewOrganization(
                    type=OrganizationType.PARTNER,
                    name=command.company_name,
                    document=command.document,
                )
            )

            user_id = await self._directory.create(
                email=command.admin_email,
                name=command.admin_name,
                password=command.admin_password,
            )

            await uow.memberships.create(
                NewMembership(
                    user_id=user_id,
                    organization_id=organization.id,
                    organization_type=organization.type,
                    role=Role.PARTNER_ADMIN,
                )
            )

            await uow.commit()
            return user_id
