from src.core.exceptions import ValidationAppError
from src.core.tenancy import CurrentOrganization, OrganizationType
from src.modules.access.application.dtos.commands import CreateAgreementCommand
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import NewPartnerAgreement, PartnerAgreement


class CreateAgreementUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de criação de convênio.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        command: CreateAgreementCommand,
    ) -> PartnerAgreement:
        """
        Vincula um Parceiro à Empresa ativa.

        As conferências de tipo aqui existem pra devolver 422 legível, **não** pra garantir a
        integridade: quem garante é o banco, via FK composta contra `organizations(id, type)`
        — um `INSERT` que passe por fora desta aplicação falha do mesmo jeito. Idem a
        unicidade do par `(company_id, partner_id)`, que vira `ConflictError` no `commit`.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada. É o lado Empresa do convênio.
            command (CreateAgreementCommand):
                O Parceiro a vincular.

        Returns:
            PartnerAgreement:
                O convênio criado.

        Raises:
            ValidationAppError:
                Se a organização ativa não for uma Empresa, ou se o `partner_id` não existir
                ou não for um Parceiro.
            ConflictError:
                Se já existir convênio entre esta Empresa e este Parceiro.
        """

        if organization.type is not OrganizationType.COMPANY:
            raise ValidationAppError("Só uma Empresa pode manter convênios com Parceiros.")

        async with self._uow as uow:
            partner = await uow.organizations.get_by_id_or_none(command.partner_id)
            if partner is None or partner.type is not OrganizationType.PARTNER:
                raise ValidationAppError("O convênio precisa apontar para um Parceiro.")

            agreement = await uow.agreements.create(
                NewPartnerAgreement(
                    company_id=organization.id,
                    partner_id=command.partner_id,
                )
            )
            await uow.commit()
            return agreement
