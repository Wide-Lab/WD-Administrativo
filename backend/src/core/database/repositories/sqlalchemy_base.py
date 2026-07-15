import uuid
from abc import ABC, abstractmethod

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.base_model import Base
from src.core.database.ports import Repository as RepositoryPort
from src.core.exceptions import NotFoundError
from src.core.pagination.params import Page, PageParams
from src.core.types import BaseCreateCommand, BaseUpdateCommand, DataclassInstance


class SQLAlchemyRepository[
    ModelT: Base,
    EntityT: DataclassInstance,
    FiltersT: DataclassInstance,
    CreateCommandT: BaseCreateCommand,
    UpdateCommandT: BaseUpdateCommand,
](
    RepositoryPort[
        EntityT,
        FiltersT,
        CreateCommandT,
        UpdateCommandT,
    ],
    ABC,
):
    """
    Repositório base para operações de banco de dados. Fornece métodos comuns como
    `get_by_id_or_none` e `delete`.
    """

    model: type[ModelT]
    filters_type: type[FiltersT]

    def __init__(self, session: AsyncSession) -> None:
        """
        Inicializa o repositório com a sessão do banco de dados.

        Args:
            session (AsyncSession):
                Sessão assíncrona do SQLAlchemy para interagir com o banco de dados.
        """

        self._session = session

    @abstractmethod
    def _to_entity(self, row: ModelT) -> EntityT: ...

    async def get_by_id_or_none(self, id_: uuid.UUID) -> EntityT | None:
        """
        Obtém uma entidade pelo seu ID. Retorna `None` se a entidade não for encontrada.

        Args:
            id_ (uuid.UUID):
                ID da entidade a ser buscada.

        Returns:
            EntityT | None:
                A entidade encontrada ou `None` se não for encontrada.
        """

        row = await self._session.get(self.model, id_)
        if row is None:
            return None
        return self._to_entity(row)

    async def get_by_id(self, id_: uuid.UUID) -> EntityT:
        """
        Obtém uma entidade pelo seu ID. Lança `NotFoundError` se a entidade não for
        encontrada.

        Args:
            id_ (uuid.UUID):
                ID da entidade a ser buscada.

        Returns:
            EntityT:
                A entidade encontrada.

        Raises:
            NotFoundError:
                Se a entidade com o ID fornecido não for encontrada.
        """

        entity = await self.get_by_id_or_none(id_)
        if entity is None:
            raise NotFoundError(f"Entidade com ID {id_} não encontrada.")
        return entity

    async def create(
        self,
        create_command: CreateCommandT,
    ) -> EntityT:
        """
        Cria uma nova entidade no banco de dados usando um comando de criação.

        Args:
            create_command (BaseCreateCommand):
                Comando de criação contendo os dados necessários para criar a entidade.

        Returns:
            EntityT:
                A entidade criada.
        """

        data = create_command.to_dict()
        obj = self.model(**data)
        self._session.add(obj)
        await self._session.flush()
        return self._to_entity(obj)

    async def update(
        self,
        id_: uuid.UUID,
        update_command: UpdateCommandT,
    ) -> EntityT:
        """
        Atualize os campos de uma entidade pelo seu ID usando um comando de atualização.
        O comando de atualização deve herdar de `BaseUpdateCommand` e usar o sentinel
        `UNSET` para campos opcionais.

        Args:
            id_ (uuid.UUID):
                ID da entidade a ser atualizada.
            update_command (BaseUpdateCommand):
                Comando de atualização contendo os campos a serem atualizados. Campos
                que não devem ser atualizados devem ser definidos como `UNSET`.

        Returns:
            EntityT:
                A entidade atualizada.

        Raises:
            NotFoundError:
                Se a entidade com o ID fornecido não for encontrada.
        """

        obj = await self._get_model_by_id(id_)
        for field, value in update_command.defined_values().items():
            setattr(obj, field, value)
        await self._session.flush()
        await self._session.refresh(obj)
        return self._to_entity(obj)

    async def delete(self, id_: uuid.UUID) -> None:
        """
        Deleta uma entidade pelo seu ID.

        Args:
            id_ (uuid.UUID):
                ID da entidade a ser deletada.

        Returns:
            None

        Raises:
            NotFoundError:
                Se a entidade com o ID fornecido não for encontrada.
        """

        stmt = sa.delete(self.model).where(self.model.id == id_)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        if result.rowcount == 0:  # type: ignore[attr-defined]
            raise NotFoundError(f"Entidade com ID {id_} não encontrada.")

    async def paginate(
        self,
        page_params: PageParams,
        filters: FiltersT | None = None,
    ) -> Page[EntityT]:
        """
        Paginação de entidades com base nos filtros fornecidos. Chama o método
        `_apply_filters` para aplicar filtros. Por padrão, não aplica filtro nenhum.

        Args:
            page_params (PageParams):
                Parâmetros de paginação, como número da página e tamanho da página.
            filters (FiltersT):
                Filtros específicos para refinar a busca de entidades. O tipo de filtros
                é definido pela classe filha e deve ser um dataclass.

        Returns:
            Page[EntityT]:
                Página de entidades que correspondem aos filtros e parâmetros de
                paginação.
        """

        filters = filters or self.filters_type()
        stmt = sa.select(self.model)
        stmt = self._apply_filters(stmt, filters)
        return await self._paginate(stmt, page_params)

    async def _paginate(
        self,
        stmt: sa.Select,
        params: PageParams,
    ) -> Page[EntityT]:
        """
        Pagina os resultados de uma consulta.

        Args:
            stmt (sa.Select):
                A consulta SQLAlchemy a ser paginada.
            params (PageParams):
                Parâmetros de paginação.

        Returns:
            Page[EntityT]:
                A página de resultados.
        """

        count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total = await self._session.scalar(count_stmt) or 0

        result = await self._session.execute(
            stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
        )
        rows = result.scalars().all()

        return Page(
            items=[self._to_entity(row) for row in rows],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def _apply_filters(
        self,
        stmt: sa.Select,
        filters: FiltersT,
    ) -> sa.Select:
        return stmt

    async def _get_model_or_none(self, id_: uuid.UUID) -> ModelT | None:
        """
        Obtém um modelo pelo seu ID. Retorna `None` se o modelo não for encontrado.

        Args:
            id_ (uuid.UUID):
                ID do modelo a ser buscado.

        Returns:
            ModelT | None:
                O modelo encontrado ou `None` se não for encontrado.
        """

        return await self._session.get(self.model, id_)

    async def _get_model_by_id(self, id_: uuid.UUID) -> ModelT:
        """
        Obtém um modelo pelo seu ID. Lança `NotFoundError` se o modelo não for
        encontrado.

        Args:
            id_ (uuid.UUID):
                ID do modelo a ser buscado.

        Returns:
            ModelT:
                O modelo encontrado.

        Raises:
            NotFoundError:
                Se o modelo com o ID fornecido não for encontrado.
        """

        obj = await self._get_model_or_none(id_)
        if obj is None:
            raise NotFoundError(f"Entidade com ID {id_} não encontrada.")
        return obj
