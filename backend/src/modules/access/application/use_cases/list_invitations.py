from datetime import UTC, datetime

from src.core.pagination.params import Page, PageParams
from src.core.tenancy import CurrentOrganization
from src.modules.access.application.dtos.filters import InvitationFilters
from src.modules.access.application.ports.unit_of_work import AccessUnitOfWorkProtocol
from src.modules.access.domain.entities import Invitation, InvitationStatus


class ListInvitationsUseCase:
    def __init__(self, uow: AccessUnitOfWorkProtocol) -> None:
        """
        Inicializa o use case de listagem de convites.

        Args:
            uow (AccessUnitOfWorkProtocol):
                Unidade de trabalho de `access`.
        """

        self._uow = uow

    async def execute(
        self,
        organization: CurrentOrganization,
        page_params: PageParams,
        status: InvitationStatus | None = None,
        now: datetime | None = None,
    ) -> Page[Invitation]:
        """
        Lista os convites da organização do path.

        Escopado pela organização ativa e não por quem pergunta: o filtro por
        `organization.id` é o que impede um `hr` de uma Empresa de enxergar quem a outra está
        convidando. Mesma escolha do `ListMembersUseCase`.

        **Sem `status`, o default é `pending`** — e não "tudo". A pergunta que esta rota
        responde primeiro é *"o que ainda está de pé pra alguém aceitar"*; o histórico de quem
        já entrou, desistiu ou venceu é uma segunda pergunta, e quem a faz a faz explicitamente.
        Um default de "tudo" faria a tela de gestão nascer mostrando ruído de meses.

        O `status` filtra pelo **efetivo**, não pela coluna: um convite vencido aparece em
        `expired` e some de `pending`, sem nada ter gravado a coluna. O `now` é resolvido aqui,
        uma vez, e desce pro repositório — assim a lista inteira responde pelo mesmo instante.

        Args:
            organization (CurrentOrganization):
                A organização do path, já validada.
            page_params (PageParams):
                Paginação.
            status (InvitationStatus | None):
                O status **efetivo** a filtrar. `None` cai no default `pending`.
            now (datetime | None):
                O instante que decide o que venceu. `None` usa o agora.

        Returns:
            Page[Invitation]:
                Os convites da organização.
        """

        async with self._uow as uow:
            return await uow.invitations.paginate(
                page_params=page_params,
                filters=InvitationFilters(
                    organization_id=organization.id,
                    status=status if status is not None else InvitationStatus.PENDING,
                    now=now if now is not None else datetime.now(UTC),
                ),
            )
