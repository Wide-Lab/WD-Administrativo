from src.core.pagination.params import Page, PageParams
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.dtos.filters import PartnerAgreementFilters
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import PartnerAgreement


class ListAgreementsUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de listagem de convênios.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        page_params: PageParams,
    ) -> Page[PartnerAgreement]:
        """
        Lista os convênios de que a organização ativa participa.

        Serve aos dois lados: a Empresa vê os Parceiros que contratou, e o Parceiro vê as
        Empresas que atende — é o mesmo convênio, lido de pontas opostas. O filtro sai da
        organização do path, nunca de query param: pedir os convênios "de outra" não é uma
        requisição que exista.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            page_params (PageParams):
                Paginação.

        Returns:
            Page[PartnerAgreement]:
                A página de convênios.
        """

        async with self._uow as uow:
            return await uow.agreements.paginate(
                page_params=page_params,
                filters=PartnerAgreementFilters(organization_id=organization.id),
            )
