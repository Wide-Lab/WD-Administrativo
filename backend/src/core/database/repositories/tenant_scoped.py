import uuid
from abc import ABC

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.repositories.sqlalchemy_base import SQLAlchemyRepository
from src.core.database.tenant import TenantScopedBase
from src.core.exceptions import NotFoundError
from src.core.pagination.params import Page, PageParams
from src.core.tenancy import OrganizationId
from src.core.types import BaseCreateCommand, BaseUpdateCommand, DataclassInstance


class TenantScopedRepository[
    ModelT: TenantScopedBase,
    EntityT: DataclassInstance,
    FiltersT: DataclassInstance,
    CreateCommandT: BaseCreateCommand,
    UpdateCommandT: BaseUpdateCommand,
](
    SQLAlchemyRepository[
        ModelT,
        EntityT,
        FiltersT,
        CreateCommandT,
        UpdateCommandT,
    ],
    ABC,
):
    """Repositório que **impõe** o escopo de tenant: nasce amarrado a uma organização e nunca
    lê nem escreve linha de outra.

    O filtro não é responsabilidade do código de negócio — é deste helper. Um use case que
    esqueça o `organization_id` continua correto, porque não existe caminho aqui que dispense
    o filtro: toda leitura passa por `_get_model_or_none` ou por `paginate`, e ambos já vêm
    com a cláusula. `create` carimba a organização; `delete` e `update` só alcançam linhas do
    próprio tenant. É o que a `03-organizacoes-e-tenancy.md` pede quando diz "pra ninguém
    esquecer o filtro".

    Um repositório destes é construído por request, a partir de `current_organization` — nunca
    de um `organization_id` que veio do corpo da requisição."""

    def __init__(self, session: AsyncSession, organization_id: OrganizationId) -> None:
        """
        Inicializa o repositório amarrado a uma organização.

        Args:
            session (AsyncSession):
                Sessão assíncrona do SQLAlchemy.
            organization_id (OrganizationId):
                A organização ativa da requisição. Vem de `current_organization`, que já
                validou o acesso de quem fez a requisição.
        """

        super().__init__(session)
        self._organization_id = organization_id

    @property
    def organization_id(self) -> OrganizationId:
        """A organização a que este repositório está amarrado."""

        return self._organization_id

    @property
    def _tenant_filter(self) -> sa.ColumnElement[bool]:
        return self.model.organization_id == self._organization_id

    async def get_by_id_or_none(self, id_: uuid.UUID) -> EntityT | None:
        """Busca por id **dentro** da organização ativa; `None` para linha de outra.

        Sobrescrever aqui não é redundância com `_get_model_or_none`: o repositório base
        resolve este método com `session.get()` direto, sem passar por `_get_model_or_none` —
        escopar só o helper deixaria este caminho furado."""

        row = await self._get_model_or_none(id_)
        if row is None:
            return None
        return self._to_entity(row)

    async def create(self, create_command: CreateCommandT) -> EntityT:
        """Cria uma entidade **já carimbada** com a organização ativa.

        O `organization_id` não vem do comando de criação de propósito: não há como o código
        de negócio gravar numa organização que não a ativa.
        """

        obj = self.model(
            **create_command.to_dict(),
            organization_id=self._organization_id,
        )
        self._session.add(obj)
        await self._session.flush()
        return self._to_entity(obj)

    async def delete(self, id_: uuid.UUID) -> None:
        """Deleta uma entidade da organização ativa. Linha de outra organização não é
        encontrada — e vira `NotFoundError`, não um delete silencioso."""

        stmt = sa.delete(self.model).where(self.model.id == id_, self._tenant_filter)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError(f"Entidade com ID {id_} não encontrada.")

    async def paginate(
        self,
        page_params: PageParams,
        filters: FiltersT | None = None,
    ) -> Page[EntityT]:
        """Pagina entidades **da organização ativa**. O filtro de tenant entra antes dos
        filtros da classe filha, que não tem como removê-lo."""

        filters = filters or self.filters_type()
        stmt = sa.select(self.model).where(self._tenant_filter)
        stmt = self._apply_filters(stmt, filters)
        return await self._paginate(stmt, page_params)

    async def _get_model_or_none(self, id_: uuid.UUID) -> ModelT | None:
        """Busca por id **dentro** da organização ativa.

        Troca o `session.get()` do repositório base por um `select` filtrado de propósito: o
        `get()` acerta a identity map pela PK e furaria o escopo de tenant. `get_by_id` e
        `update` chegam aqui pelo `_get_model_by_id` do base."""

        result = await self._session.execute(
            sa.select(self.model).where(
                self.model.id == id_,  # type: ignore[attr-defined]
                self._tenant_filter,
            )
        )
        return result.scalars().one_or_none()
