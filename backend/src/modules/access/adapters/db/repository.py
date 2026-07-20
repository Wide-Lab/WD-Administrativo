import uuid
from datetime import UTC, datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.modules import ModuleKey
from src.core.pagination.params import Page, PageParams
from src.core.tenancy import OrganizationType
from src.modules.access.adapters.db.models import Invitation as InvitationModel
from src.modules.access.adapters.db.models import Membership as MembershipModel
from src.modules.access.adapters.db.models import ModuleEntitlement as ModuleEntitlementModel
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.adapters.db.models import PartnerAgreement as PartnerAgreementModel
from src.modules.access.application.dtos.filters import (
    InvitationFilters,
    MembershipFilters,
    OrganizationFilters,
    PartnerAgreementFilters,
)
from src.modules.access.domain.entities import (
    Invitation,
    InvitationStatus,
    InvitationWithOrganization,
    Membership,
    MembershipStatus,
    MembershipWithOrganization,
    ModuleEntitlement,
    NewInvitation,
    NewMembership,
    NewModuleEntitlement,
    NewOrganization,
    NewPartnerAgreement,
    Organization,
    OrganizationStatus,
    PartnerAgreement,
    Role,
    UpdateInvitation,
    UpdateMembership,
    UpdateOrganization,
    UpdatePartnerAgreement,
)


def _organization_to_entity(row: OrganizationModel) -> Organization:
    """Model → entidade. É função de módulo, e não só método do `OrganizationRepository`,
    porque o `MembershipRepository` também precisa dela: `GET /api/me/contexto` devolve o
    vínculo já com a organização do outro lado."""

    return Organization(
        id=row.id,
        type=row.type,
        name=row.name,
        document=row.document,
        status=row.status,
        created_at=row.created_at,
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
        return _organization_to_entity(row)


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


class ModuleEntitlementRepository:
    """Repositório de entitlements de módulo — o que cada Empresa contratou.

    Não é tenant-scoped pelo helper do `core` pelo mesmo motivo que `organizations` não é: o
    entitlement é dado **sobre** um tenant, não dado *dentro* de um. Quem escopa é o filtro
    explícito por `organization_id` de cada método — não há leitura que não o receba."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_organization_and_module(
        self,
        organization_id: uuid.UUID,
        module_key: ModuleKey,
    ) -> ModuleEntitlement | None:
        """O entitlement de um módulo numa organização; `None` se o módulo não está habilitado
        — presença da linha é o "sim"."""

        row = await self._get_model_by(
            sa.and_(
                ModuleEntitlementModel.organization_id == organization_id,
                ModuleEntitlementModel.module_key == module_key,
            )
        )
        return self._to_entity(row) if row else None

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[ModuleEntitlement]:
        """Os módulos habilitados de uma organização, ordenados por chave."""

        result = await self._session.execute(
            sa.select(ModuleEntitlementModel)
            .where(ModuleEntitlementModel.organization_id == organization_id)
            .order_by(ModuleEntitlementModel.module_key)
        )
        return [self._to_entity(row) for row in result.scalars().all()]

    async def create(self, create_command: NewModuleEntitlement) -> ModuleEntitlement:
        """Habilita um módulo. Como no convênio (spec 03), a violação de constraint vira
        `ConflictError` já no `flush` — é dali que sai o `INSERT`, e sem esta tradução um
        entitlement duplicado viraria 500.

        Quem chama é o `EnableModuleUseCase`, que só chega aqui se a linha não existir: o `PUT`
        é idempotente. O conflito que sobra é a corrida entre dois `PUT` simultâneos."""

        model = ModuleEntitlementModel(**create_command.to_dict())
        self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Este módulo já está habilitado nesta organização.") from exc

        return self._to_entity(model)

    async def delete(self, organization_id: uuid.UUID, module_key: ModuleKey) -> bool:
        """Desabilita um módulo apagando a linha — não há coluna pra desligar.

        Devolve se havia o que apagar. Apagar o que não existe não é erro: o `DELETE` afirma um
        estado, e quem chama decide se a diferença importa (hoje não importa — a rota responde
        204 nos dois casos)."""

        model = await self._get_model_by(
            sa.and_(
                ModuleEntitlementModel.organization_id == organization_id,
                ModuleEntitlementModel.module_key == module_key,
            )
        )
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def _get_model_by(
        self,
        condition: sa.ColumnElement[bool],
    ) -> ModuleEntitlementModel | None:
        result = await self._session.execute(sa.select(ModuleEntitlementModel).where(condition))
        return result.scalars().one_or_none()

    def _to_entity(self, row: ModuleEntitlementModel) -> ModuleEntitlement:
        return ModuleEntitlement(
            id=row.id,
            organization_id=row.organization_id,
            module_key=row.module_key,
            granted_at=row.granted_at,
            granted_by=row.granted_by,
        )


class MembershipRepository:
    """Repositório de vínculos usuário↔organização↔papel.

    Não é tenant-scoped pelo helper do `core`: o vínculo é *a definição* de tenant de alguém,
    e o `/me/contexto` precisa justamente atravessar organizações pra listar onde a pessoa
    entra. Quem escopa a leitura por organização é o filtro explícito de cada use case."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_or_none(self, id_: uuid.UUID) -> Membership | None:
        row = await self._get_model_by(MembershipModel.id == id_)
        return self._to_entity(row) if row else None

    async def create(self, create_command: NewMembership) -> Membership:
        """Cria um vínculo. A unicidade `(user_id, organization_id)` e a validade do papel pro
        tipo de organização são garantidas pelo banco; aqui a violação vira `ConflictError`.

        Como no convênio (spec 03), a tradução precisa acontecer no `flush` e não só no
        `commit`: o `INSERT` sai daqui, então a constraint estoura antes — sem este `except`,
        um vínculo duplicado viraria 500 em vez de 409."""

        model = MembershipModel(**create_command.to_dict())
        self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Esta pessoa já tem vínculo com esta organização.") from exc

        return self._to_entity(model)

    async def update(self, id_: uuid.UUID, update_command: UpdateMembership) -> Membership:
        """Atualiza papel e/ou status. `organization_type` não está entre os campos: ele
        acompanha a organização, não o vínculo — e é o CHECK do banco que recusa um papel
        incompatível com ele."""

        model = await self._get_model_by(MembershipModel.id == id_)
        if model is None:
            raise NotFoundError("Vínculo não encontrado.")

        for field, value in update_command.defined_values().items():
            setattr(model, field, value)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Papel inválido para o tipo desta organização.") from exc

        return self._to_entity(model)

    async def paginate(
        self,
        page_params: PageParams,
        filters: MembershipFilters | None = None,
    ) -> Page[Membership]:
        filters = filters or MembershipFilters()

        stmt = sa.select(MembershipModel)
        if filters.organization_id is not None:
            stmt = stmt.where(MembershipModel.organization_id == filters.organization_id)
        if filters.user_id is not None:
            stmt = stmt.where(MembershipModel.user_id == filters.user_id)
        if filters.role is not None:
            stmt = stmt.where(MembershipModel.role == filters.role)
        if filters.status is not None:
            stmt = stmt.where(MembershipModel.status == filters.status)
        stmt = stmt.order_by(MembershipModel.created_at.desc())

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

    async def get_active_for_user_and_organization(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> Membership | None:
        """O vínculo ativo de uma pessoa numa organização; `None` se não houver.

        "Ativo" exige o vínculo **e** a organização ativos: desativar uma organização derruba
        o acesso de todo mundo nela sem tocar vínculo por vínculo, e desativar um vínculo
        derruba a pessoa sem apagar o histórico dela."""

        result = await self._session.execute(
            sa.select(MembershipModel)
            .join(OrganizationModel, MembershipModel.organization_id == OrganizationModel.id)
            .where(
                MembershipModel.user_id == user_id,
                MembershipModel.organization_id == organization_id,
                MembershipModel.status == MembershipStatus.ACTIVE,
                OrganizationModel.status == OrganizationStatus.ACTIVE,
            )
        )
        row = result.scalars().one_or_none()
        return self._to_entity(row) if row else None

    async def is_platform_admin(self, user_id: uuid.UUID) -> bool:
        """Se a pessoa é admin da plataforma — vínculo `platform_admin` ativo na organização
        `platform`.

        Não recebe organização de propósito: é o único papel cuja pergunta não é "nesta
        organização". A Widelab opera o SaaS e alcança qualquer tenant."""

        result = await self._session.execute(
            sa.select(MembershipModel.id)
            .join(OrganizationModel, MembershipModel.organization_id == OrganizationModel.id)
            .where(
                MembershipModel.user_id == user_id,
                MembershipModel.role == Role.PLATFORM_ADMIN,
                MembershipModel.status == MembershipStatus.ACTIVE,
                OrganizationModel.type == OrganizationType.PLATFORM,
                OrganizationModel.status == OrganizationStatus.ACTIVE,
            )
            .limit(1)
        )
        return result.scalars().one_or_none() is not None

    async def list_active_for_user(self, user_id: uuid.UUID) -> list[MembershipWithOrganization]:
        """Os vínculos ativos de uma pessoa, já com a organização de cada um — o payload do
        `GET /api/me/contexto`.

        Vínculo desativado ou organização desativada não entram: o contexto é a lista do que a
        pessoa *pode* abrir agora, e é dela que o frontend monta o seletor de organização.
        Devolver uma organização que o `current_organization` negaria em seguida seria oferecer
        uma porta trancada."""

        result = await self._session.execute(
            sa.select(MembershipModel, OrganizationModel)
            .join(OrganizationModel, MembershipModel.organization_id == OrganizationModel.id)
            .where(
                MembershipModel.user_id == user_id,
                MembershipModel.status == MembershipStatus.ACTIVE,
                OrganizationModel.status == OrganizationStatus.ACTIVE,
            )
            .order_by(OrganizationModel.name)
        )

        return [
            MembershipWithOrganization(
                membership=self._to_entity(membership),
                organization=_organization_to_entity(organization),
            )
            for membership, organization in result.all()
        ]

    async def _get_model_by(self, condition: sa.ColumnElement[bool]) -> MembershipModel | None:
        result = await self._session.execute(sa.select(MembershipModel).where(condition))
        return result.scalars().one_or_none()

    def _to_entity(self, row: MembershipModel) -> Membership:
        return Membership(
            id=row.id,
            user_id=row.user_id,
            organization_id=row.organization_id,
            role=row.role,
            status=row.status,
            created_at=row.created_at,
        )


def _effective_status_condition(
    status: InvitationStatus,
    now: datetime,
) -> sa.ColumnElement[bool]:
    """O gêmeo em SQL de `Invitation.effective_status` — a mesma regra, escrita onde o `WHERE`
    a alcança.

    Ela **precisa** viver no SQL, e não num `filter()` sobre a página já lida: o `total` da
    paginação sai de um `COUNT` sobre esta mesma query, e filtrar depois faria a lista contar
    vencidos como pendentes e devolver menos itens do que o número que ela própria anuncia.
    Paginação que mente é pior que paginação que falta.

    **São duas escritas da mesma decisão, e é dívida assumida** — quem mexer em
    `effective_status` tem que mexer aqui. O que segura as duas juntas é um teste que compara
    as duas leituras convite a convite; sem ele, elas divergem em silêncio."""

    match status:
        case InvitationStatus.PENDING:
            return sa.and_(
                InvitationModel.status == InvitationStatus.PENDING,
                InvitationModel.expires_at > now,
            )
        case InvitationStatus.EXPIRED:
            # Vencido é `pending` na **coluna** — `expired` nunca é gravado (spec 06). Sem esta
            # linha, filtrar por `expired` devolveria sempre vazio.
            return sa.and_(
                InvitationModel.status == InvitationStatus.PENDING,
                InvitationModel.expires_at <= now,
            )
        case InvitationStatus.ACCEPTED | InvitationStatus.REVOKED:
            # Terminais: a coluna já é a verdade, e nenhum relógio os move.
            return InvitationModel.status == status


class InvitationRepository:
    """Repositório de convites.

    Não é tenant-scoped pelo helper do `core`, e aqui a razão é mais forte que nas outras:
    as duas leituras por token são **públicas** — quem aceita um convite ainda não tem sessão,
    quanto mais organização ativa. O que escopa é o próprio token, que é a credencial.

    As leituras de **gestão** (spec 08) são o outro caso: elas têm sessão e organização ativa,
    e recebem o `organization_id` explicitamente em cada método. Nenhuma delas o infere."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_or_none(self, id_: uuid.UUID) -> Invitation | None:
        """Um convite por id, sem escopo de organização.

        Quem confere o tenant é o use case, que precisa distinguir "não existe" de "existe e é
        de outra Empresa" — as duas viram 404, mas por caminhos que o código nomeia."""

        row = await self._get_model_by(InvitationModel.id == id_)
        return self._to_entity(row) if row else None

    async def get_by_token_or_none(self, token: str) -> Invitation | None:
        row = await self._get_model_by(InvitationModel.token == token)
        return self._to_entity(row) if row else None

    async def get_with_organization_by_token(
        self,
        token: str,
    ) -> InvitationWithOrganization | None:
        """O convite já com a organização que convidou — a tela pública de aceite mostra o nome
        dela, e uma segunda consulta pra isso seria desperdício."""

        result = await self._session.execute(
            sa.select(InvitationModel, OrganizationModel)
            .join(OrganizationModel, InvitationModel.organization_id == OrganizationModel.id)
            .where(InvitationModel.token == token)
        )
        row = result.one_or_none()
        if row is None:
            return None

        invitation, organization = row
        return InvitationWithOrganization(
            invitation=self._to_entity(invitation),
            organization=_organization_to_entity(organization),
        )

    async def create(self, create_command: NewInvitation) -> Invitation:
        """Cria um convite. Como nos outros repositórios, a violação de constraint vira
        `ConflictError` já no `flush` — sem isto, um papel inválido pro tipo da organização
        (o CHECK) viraria 500 em vez de resposta legível."""

        model = InvitationModel(**create_command.to_dict())
        self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Não foi possível criar o convite.") from exc

        return self._to_entity(model)

    async def update(self, id_: uuid.UUID, update_command: UpdateInvitation) -> Invitation:
        model = await self._get_model_by(InvitationModel.id == id_)
        if model is None:
            raise NotFoundError("Convite não encontrado.")

        for field, value in update_command.defined_values().items():
            setattr(model, field, value)

        await self._session.flush()
        return self._to_entity(model)

    async def mark_accepted_if_pending(self, id_: uuid.UUID) -> bool:
        """Gasta o convite, e devolve se **esta** chamada foi quem o gastou.

        É um `UPDATE ... WHERE status = 'pending'` condicional, e não um `read` seguido de
        `write`, porque é isto que faz o uso único ser único de verdade: dois aceites
        simultâneos do mesmo token passariam os dois pela checagem de status e criariam dois
        vínculos. Aqui o segundo recebe `False` — o banco decide quem chegou primeiro.

        Não confere expiração: quem já sabe disso é o use case, via `effective_status`. Este
        método responde só "ainda estava por gastar?"."""

        # `execute` é tipado como `Result[Any]`, que não conhece `rowcount`; um `UPDATE` sempre
        # devolve um `CursorResult`, e é dele que sai a contagem de linhas afetadas.
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                sa.update(InvitationModel)
                .where(
                    InvitationModel.id == id_,
                    InvitationModel.status == InvitationStatus.PENDING,
                )
                .values(status=InvitationStatus.ACCEPTED)
            ),
        )
        return result.rowcount == 1

    async def mark_revoked_if_pending(
        self,
        id_: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> bool:
        """Revoga o convite, e devolve se **esta** chamada foi quem o revogou.

        Mesma forma do `mark_accepted_if_pending`, e pelo mesmo motivo: é um `UPDATE ... WHERE
        status = 'pending'`, e não um `if` sobre um status lido antes. É o banco que decide a
        corrida — dois `DELETE` simultâneos, ou um `DELETE` competindo com o aceite —, e quem
        chega primeiro leva o `pending`. O outro recebe `False` e vai perguntar por quê.

        O `organization_id` entra **no mesmo `WHERE`**, e não numa conferência antes: assim não
        existe janela entre "confirmei que é minha" e "escrevi". Um id de outra Empresa
        simplesmente não casa, e a linha dela não é tocada nem por um instante.

        A revogação é **soft** — grava o status, mantém a linha. A linha é o registro de quem
        convidou quem, e o aceite precisa dela pra recusar com 410 em vez de 404.

        Note que um convite **vencido** casa com este `WHERE`: a coluna dele é `pending`
        (`expired` nunca é gravado). Revogá-lo é 204 e grava `revoked`, o que é a resposta certa
        — quem revoga está dizendo "este convite não vale", e ele já não valia."""

        result = cast(
            CursorResult[Any],
            await self._session.execute(
                sa.update(InvitationModel)
                .where(
                    InvitationModel.id == id_,
                    InvitationModel.organization_id == organization_id,
                    InvitationModel.status == InvitationStatus.PENDING,
                )
                .values(status=InvitationStatus.REVOKED)
            ),
        )
        return result.rowcount == 1

    async def paginate(
        self,
        page_params: PageParams,
        filters: InvitationFilters | None = None,
    ) -> Page[Invitation]:
        """Os convites de uma organização, filtrados pelo status **efetivo**.

        O filtro de status não olha a coluna crua: ver `_effective_status_condition`."""

        filters = filters or InvitationFilters()

        stmt = sa.select(InvitationModel)
        if filters.organization_id is not None:
            stmt = stmt.where(InvitationModel.organization_id == filters.organization_id)
        if filters.status is not None:
            stmt = stmt.where(
                _effective_status_condition(
                    filters.status,
                    filters.now if filters.now is not None else datetime.now(UTC),
                )
            )
        stmt = stmt.order_by(InvitationModel.created_at.desc())

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

    async def _get_model_by(self, condition: sa.ColumnElement[bool]) -> InvitationModel | None:
        result = await self._session.execute(sa.select(InvitationModel).where(condition))
        return result.scalars().one_or_none()

    def _to_entity(self, row: InvitationModel) -> Invitation:
        return Invitation(
            id=row.id,
            email=row.email,
            organization_id=row.organization_id,
            role=row.role,
            token=row.token,
            status=row.status,
            expires_at=row.expires_at,
            invited_by=row.invited_by,
            created_at=row.created_at,
        )
