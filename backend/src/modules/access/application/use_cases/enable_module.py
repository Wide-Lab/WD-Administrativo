from src.core.exceptions import ValidationAppError
from src.core.modules import ModuleKey, is_registered, registered_modules
from src.core.security import UserId
from src.core.tenancy import CurrentOrganization, OrganizationType
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import ModuleEntitlement, NewModuleEntitlement


class EnableModuleUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de habilitação de módulo.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        module_key: ModuleKey,
        granted_by: UserId,
    ) -> ModuleEntitlement:
        """
        Habilita um módulo numa Empresa — a venda, que é ligar um flag e não fazer um deploy.

        **Idempotente**: habilitar de novo devolve o entitlement que já existe, sem escrever.
        Não é conveniência de API, é o que o modelo permite dizer — a linha é o "sim", e um
        segundo "sim" não é um sim diferente. Quem impede a linha repetida de verdade é o único
        `(organization_id, module_key)` no banco, que num `PUT` simultâneo vira 409.

        A conferência de tipo aqui existe pra devolver 422 legível, **não** pra garantir a
        integridade: quem garante é a FK composta contra `organizations(id, type)` com o tipo
        fixado em coluna gerada — um `INSERT` por fora da aplicação falha do mesmo jeito. A
        conferência da chave no registry é o oposto: essa **só** existe aqui, porque o registro
        de módulos é código e o banco não tem como enxergá-lo.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada. É a Empresa que contrata.
            module_key (ModuleKey):
                A chave do módulo a habilitar.
            granted_by (UserId):
                O `platform_admin` que liberou.

        Returns:
            ModuleEntitlement:
                O entitlement — o que acabou de nascer, ou o que já existia.

        Raises:
            ValidationAppError:
                Se a organização não for uma Empresa, ou se a chave não existir no registry.
        """

        if organization.type is not OrganizationType.COMPANY:
            raise ValidationAppError("Só uma Empresa contrata módulos.")

        if not is_registered(module_key):
            known = ", ".join(descriptor.key for descriptor in registered_modules())
            raise ValidationAppError(
                f"A plataforma não conhece o módulo '{module_key}'. Módulos: {known}."
            )

        async with self._uow as uow:
            existing = await uow.module_entitlements.get_by_organization_and_module(
                organization_id=organization.id,
                module_key=module_key,
            )
            if existing is not None:
                return existing

            entitlement = await uow.module_entitlements.create(
                NewModuleEntitlement(
                    organization_id=organization.id,
                    module_key=module_key,
                    granted_by=granted_by,
                )
            )
            await uow.commit()
            return entitlement
