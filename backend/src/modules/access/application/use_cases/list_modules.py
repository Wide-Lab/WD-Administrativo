from dataclasses import dataclass

from src.core.modules import ModuleDescriptor, registered_modules
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import ModuleEntitlement


@dataclass(frozen=True, slots=True)
class OrganizationModules:
    """O que esta Empresa contratou, e o que existe pra contratar.

    As duas listas não se repetem e respondem perguntas diferentes: `enabled` são fatos sobre
    **este tenant** (quem ligou, quando), `catalog` é o que a **plataforma** sabe oferecer. Quem
    cruza as duas pela chave é quem monta a tela."""

    enabled: list[ModuleEntitlement]
    catalog: tuple[ModuleDescriptor, ...]


class ListModulesUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de listagem de módulos de uma organização.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(self, organization: CurrentOrganization) -> OrganizationModules:
        """
        Lista os módulos habilitados da organização do path, junto do catálogo da plataforma.

        Uma organização que não é Empresa devolve `enabled` vazio em vez de erro: ela de fato
        não contratou nada — só Empresa contrata —, e a pergunta continua tendo resposta.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.

        Returns:
            OrganizationModules:
                Os entitlements da organização e o catálogo do registry.
        """

        async with self._uow as uow:
            enabled = await uow.module_entitlements.list_for_organization(organization.id)

        return OrganizationModules(enabled=enabled, catalog=registered_modules())
