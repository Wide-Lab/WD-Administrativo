import uuid

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination.params import Page, PageParams
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.adapters.db.models import PartnerAgreement as PartnerAgreementModel
from src.modules.access.application.dtos.filters import (
    OrganizationFilters,
    PartnerAgreementFilters,
)
from src.modules.access.domain.entities import (
    NewOrganization,
    NewPartnerAgreement,
    Organization,
    PartnerAgreement,
    UpdateOrganization,
    UpdatePartnerAgreement,
)


class OrganizationRepository:
    """Repositório de organizações. Devolve entidades de domínio — o model SQLAlchemy nunca
    atravessa a fronteira do módulo.

    Não é tenant-scoped de propósito: organizações **são** os tenants, não dado dentro de um.
    Quem escopa o acesso a elas é `current_organization`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_or_none(self, id_: uuid.UUID) -> Organization | None:
        row = await self._get_model_by(OrganizationModel.id == id_)
        return self._to_entity(row) if row else None

    async def create(self, create_command: NewOrganization) -> Organization:
        """Cria uma organização. O `commit` é do chamador, via unit of work."""

        model = OrganizationModel(**create_command.to_dict())
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, id_: uuid.UUID, update_command: UpdateOrganization) -> Organization:
        """Atualiza os campos informados. `type` não está entre eles — é imutável."""

        model = await self._get_model_by(OrganizationModel.id == id_)
        if model is None:
            raise NotFoundError("Organização não encontrada.")

        for field, value in update_command.defined_values().items():
            setattr(model, field, value)

        await self._session.flush()
        return self._to_entity(model)

    async def paginate(
        self,
        page_params: PageParams,
        filters: OrganizationFilters | None = None,
    ) -> Page[Organization]:
        filters = filters or OrganizationFilters()

        stmt = sa.select(OrganizationModel)
        if filters.type is not None:
            stmt = stmt.where(OrganizationModel.type == filters.type)
        stmt = stmt.order_by(OrganizationModel.created_at.desc())

        count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total = await self._session.scalar(count_stmt) or 0

        result = await self._session.execute(
            stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
        )

        return Page(
            items=[self._to_entity(row) for row in result.scalars().all()],
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def _get_model_by(self, condition: sa.ColumnElement[bool]) -> OrganizationModel | None:
        result = await self._session.execute(sa.select(OrganizationModel).where(condition))
        return result.scalars().one_or_none()

    def _to_entity(self, row: OrganizationModel) -> Organization:
        return Organization(
            id=row.id,
            type=row.type,
            name=row.name,
            document=row.document,
            status=row.status,
            created_at=row.created_at,
        )


class PartnerAgreementRepository:
    """Repositório de convênios Empresa↔Parceiro."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_or_none(self, id_: uuid.UUID) -> PartnerAgreement | None:
        row = await self._get_model_by(PartnerAgreementModel.id == id_)
        return self._to_entity(row) if row else None

    async def create(self, create_command: NewPartnerAgreement) -> PartnerAgreement:
        """Cria um convênio. A unicidade do par e o tipo dos dois lados são garantidos pelo
        banco, e é aqui que a violação vira `ConflictError`.

        A tradução precisa acontecer neste ponto, e não só no `commit` do
        `SQLAlchemyUnitOfWork`: o `flush` abaixo já manda o `INSERT`, então a constraint
        estoura *antes* do commit — sem este `except`, um convênio duplicado viraria 500 em
        vez de 409."""

        model = PartnerAgreementModel(**create_command.to_dict())
        self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "Já existe um convênio entre esta Empresa e este Parceiro."
            ) from exc

        return self._to_entity(model)

    async def update(
        self,
        id_: uuid.UUID,
        update_command: UpdatePartnerAgreement,
    ) -> PartnerAgreement:
        model = await self._get_model_by(PartnerAgreementModel.id == id_)
        if model is None:
            raise NotFoundError("Convênio não encontrado.")

        for field, value in update_command.defined_values().items():
            setattr(model, field, value)

        await self._session.flush()
        return self._to_entity(model)

    async def paginate(
        self,
        page_params: PageParams,
        filters: PartnerAgreementFilters | None = None,
    ) -> Page[PartnerAgreement]:
        filters = filters or PartnerAgreementFilters()

        stmt = sa.select(PartnerAgreementModel)
        if filters.organization_id is not None:
            # Os dois lados enxergam o convênio: a Empresa vê seus Parceiros, o Parceiro vê as
            # Empresas que atende.
            stmt = stmt.where(
                sa.or_(
                    PartnerAgreementModel.company_id == filters.organization_id,
                    PartnerAgreementModel.partner_id == filters.organization_id,
                )
            )
        stmt = stmt.order_by(PartnerAgreementModel.created_at.desc())

        count_stmt = sa.select(sa.func.count()).select_from(stmt.subquery())
        total = await self._session.scalar(count_stmt) or 0

        result = await self._session.execute(
            stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
        )

        return Page(
            items=[self._to_entity(row) for row in result.scalars().all()],
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def _get_model_by(
        self,
        condition: sa.ColumnElement[bool],
    ) -> PartnerAgreementModel | None:
        result = await self._session.execute(sa.select(PartnerAgreementModel).where(condition))
        return result.scalars().one_or_none()

    def _to_entity(self, row: PartnerAgreementModel) -> PartnerAgreement:
        return PartnerAgreement(
            id=row.id,
            company_id=row.company_id,
            partner_id=row.partner_id,
            status=row.status,
            created_at=row.created_at,
        )
