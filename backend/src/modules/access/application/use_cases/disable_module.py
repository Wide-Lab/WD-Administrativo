from src.core.modules import ModuleKey
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol


class DisableModuleUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de desabilitação de módulo.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(self, organization: CurrentOrganization, module_key: ModuleKey) -> None:
        """
        Desabilita um módulo numa Empresa apagando o entitlement — não há flag pra desligar.

        Não valida a chave contra o registry, e é de propósito: o dia em que um módulo for
        aposentado do código, as linhas dele continuam no banco, e recusar o `DELETE` de uma
        chave desconhecida seria trancar a única porta que limpa o que sobrou. Ligar exige que o
        módulo exista; desligar, não.

        Idempotente pelo mesmo motivo que o `PUT`: o `DELETE` afirma um estado ("este módulo não
        está habilitado aqui"), e afirmá-lo de novo não é erro. Numa organização que nem podia
        ter contratado, o estado já é esse — daí nenhuma conferência de tipo.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            module_key (ModuleKey):
                A chave do módulo a desabilitar.
        """

        async with self._uow as uow:
            await uow.module_entitlements.delete(
                organization_id=organization.id,
                module_key=module_key,
            )
            await uow.commit()
