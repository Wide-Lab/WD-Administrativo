"""Os repositórios da frota.

Os três herdam de `TenantScopedRepository`: nascem amarrados à organização ativa e não têm
caminho que dispense o filtro de tenant. Um use case que esqueça o `organization_id` continua
correto — é o que a `03` pede quando diz "pra ninguém esquecer o filtro"."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy import CursorResult
from sqlalchemy.exc import IntegrityError

from src.core.database.repositories.tenant_scoped import TenantScopedRepository
from src.core.exceptions import ConflictError
from src.core.pagination.params import Page, PageParams
from src.modules.frota.adapters.db.models import Driver as DriverModel
from src.modules.frota.adapters.db.models import OdometerReading as OdometerReadingModel
from src.modules.frota.adapters.db.models import Vehicle as VehicleModel
from src.modules.frota.adapters.db.models import VehicleUsage as VehicleUsageModel
from src.modules.frota.application.dtos.filters import (
    DriverFilters,
    OdometerReadingFilters,
    VehicleFilters,
    VehicleUsageFilters,
)
from src.modules.frota.domain.entities import (
    Driver,
    NewDriver,
    NewOdometerReading,
    NewVehicle,
    NewVehicleUsage,
    OdometerReading,
    UpdateDriver,
    UpdateOdometerReading,
    UpdateVehicle,
    UpdateVehicleUsage,
    Vehicle,
    VehicleUsage,
)
from src.modules.frota.domain.rules import UsageForReport


def _constraint_of(exc: IntegrityError) -> str | None:
    """O nome da constraint que o Postgres recusou, quando ele o informa.

    Existe porque um `INSERT` em `vehicle_usages` pode violar **várias** coisas diferentes (a
    exclusão de período, as FKs compostas, os três CHECKs) e cada uma merece uma resposta
    própria. Sem olhar o nome, tudo viraria o mesmo 409 genérico e o usuário não saberia se
    digitou a data errada ou escolheu um carro de outra Empresa.

    **Percorre a cadeia de `__cause__`, e não só o `exc.orig`** — isso custou uma rodada de
    testes vermelhos. O `exc.orig` de um `IntegrityError` do asyncpg é o erro **já traduzido**
    pelo dialeto (`sqlalchemy.dialects.postgresql.asyncpg.IntegrityError`), que não carrega
    `constraint_name`; quem o carrega é a `asyncpg.exceptions.UniqueViolationError` original, um
    nível abaixo. Olhar só o topo devolvia `None` sempre, e toda violação virava 500 em vez da
    resposta que ela merece.

    O `getattr` cobre o caso de outro driver (ou de um erro sem constraint nomeada) sem quebrar
    a tradução."""

    erro: BaseException | None = exc.orig
    while erro is not None:
        nome = getattr(erro, "constraint_name", None)
        if nome:
            return str(nome)
        erro = erro.__cause__

    return None


_usage_odometers = (
    sa.select(
        VehicleUsageModel.vehicle_id.label("vehicle_id"),
        sa.func.max(VehicleUsageModel.end_odometer).label("max_end"),
        sa.func.max(VehicleUsageModel.start_odometer).label("max_start"),
    )
    .group_by(VehicleUsageModel.vehicle_id)
    .subquery("usage_odometers")
)
"""O maior hodômetro já registrado de cada veículo, num agregado só.

É o que faz `current_odometer` sair por **um** `LEFT JOIN` em vez de uma consulta por linha — o
N+1 que o critério 7 proíbe. Não filtra por tenant porque o `vehicle_id` do lado de fora já está
escopado: um veículo pertence a uma Empresa só, e o join herda o recorte."""

_CURRENT_ODOMETER = sa.func.greatest(
    VehicleModel.initial_odometer,
    sa.func.coalesce(_usage_odometers.c.max_end, 0),
    sa.func.coalesce(_usage_odometers.c.max_start, 0),
).label("current_odometer")
"""O hodômetro atual do veículo — **derivado, nunca coluna**.

O `start_odometer` de viagem **aberta** entra no `GREATEST` porque um carro na rua já rodou:
ignorá-lo faria o prior de um veículo em viagem apontar pra antes da saída. O `COALESCE(…, 0)`
cobre o veículo sem viagem nenhuma, em que o `MAX` de zero linhas é `NULL`."""


class VehicleRepository(
    TenantScopedRepository[
        VehicleModel,
        Vehicle,
        VehicleFilters,
        NewVehicle,
        UpdateVehicle,
    ]
):
    model = VehicleModel
    filters_type = VehicleFilters

    def _select_with_odometer(self) -> sa.Select:
        return sa.select(VehicleModel, _CURRENT_ODOMETER).outerjoin(
            _usage_odometers,
            _usage_odometers.c.vehicle_id == VehicleModel.id,
        )

    async def get_by_id_or_none(self, id_: uuid.UUID) -> Vehicle | None:
        """Um veículo da Empresa ativa, **já com o `current_odometer`**.

        Sobrescreve o do `TenantScopedRepository` porque aquele resolve por `select(self.model)`,
        e o hodômetro atual não é coluna: ele sai do join acima."""

        result = await self._session.execute(
            self._select_with_odometer().where(VehicleModel.id == id_, self._tenant_filter)
        )
        row = result.one_or_none()
        return self._to_entity_with(row[0], row[1]) if row is not None else None

    async def paginate(
        self,
        page_params: PageParams,
        filters: VehicleFilters | None = None,
    ) -> Page[Vehicle]:
        """A página de veículos, cada um com o hodômetro atual — em **uma** query.

        Não reusa o `_paginate` do `core` porque aquele faz `result.scalars()`, que descarta toda
        coluna depois da primeira — e é justamente na segunda que o `current_odometer` vem."""

        filters = filters or self.filters_type()
        stmt = self._apply_filters(self._select_with_odometer().where(self._tenant_filter), filters)

        total = await self._session.scalar(
            sa.select(sa.func.count()).select_from(stmt.subquery())
        )
        result = await self._session.execute(
            stmt.offset((page_params.page - 1) * page_params.page_size).limit(
                page_params.page_size
            )
        )

        return Page(
            items=[self._to_entity_with(row, current) for row, current in result.all()],
            total=total or 0,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def create(self, create_command: NewVehicle) -> Vehicle:
        """Cadastra um veículo. A placa duplicada **na mesma Empresa** é recusada pelo `UNIQUE`,
        e é aqui que a violação vira 409.

        A tradução acontece no `flush` e não só no `commit` pelo motivo de sempre neste projeto:
        o `INSERT` sai daqui, então a constraint estoura antes — sem este `except`, uma placa
        repetida viraria 500."""

        try:
            created = await super().create(create_command)
        except IntegrityError as exc:
            if _constraint_of(exc) == "uq_vehicles_organization_plate":
                raise ConflictError(
                    f"Já existe um veículo com a placa '{create_command.plate}' nesta Empresa."
                ) from exc
            raise

        return await self._reread(created.id)

    async def update(self, id_: uuid.UUID, update_command: UpdateVehicle) -> Vehicle:
        try:
            await super().update(id_, update_command)
        except IntegrityError as exc:
            if _constraint_of(exc) == "uq_vehicles_organization_plate":
                raise ConflictError("Já existe um veículo com esta placa nesta Empresa.") from exc
            raise

        return await self._reread(id_)

    async def _reread(self, id_: uuid.UUID) -> Vehicle:
        """Relê o veículo pelo caminho com join, depois de escrever.

        Custa um `SELECT` a mais em `POST` e `PATCH`, e é de propósito: o `create`/`update` do
        `core` devolve a entidade montada só do model, e ali o `current_odometer` seria um
        palpite — o `initial_odometer` de um carro que pode ter dez viagens registradas. Escrita
        de veículo é rara; devolver um número errado, não."""

        vehicle = await self.get_by_id_or_none(id_)
        if vehicle is None:  # pragma: no cover — a linha acabou de ser escrita nesta transação
            raise ConflictError("O veículo desapareceu durante a operação.")
        return vehicle

    async def labels(self) -> dict[uuid.UUID, str]:
        """`{id: placa}` de todos os veículos da Empresa — o rótulo das linhas do relatório.

        Traz a frota inteira sem paginar, e isso é deliberado: a frota de uma Empresa tem dezenas
        de carros, não milhões, e o relatório precisa nomear **qualquer** veículo que apareça no
        período — inclusive um já `inactive`, que um filtro por status esconderia."""

        result = await self._session.execute(
            sa.select(VehicleModel.id, VehicleModel.plate).where(self._tenant_filter)
        )
        return {id_: plate for id_, plate in result.all()}

    def _apply_filters(self, stmt: sa.Select, filters: VehicleFilters) -> sa.Select:
        if filters.status is not None:
            stmt = stmt.where(VehicleModel.status == filters.status)
        return stmt.order_by(VehicleModel.plate)

    def _to_entity(self, row: VehicleModel) -> Vehicle:
        """**Não é o caminho normal.** Todo acesso público desta classe passa pelo join, e é de
        lá que o `current_odometer` vem; este overload existe só porque o repositório base o
        declara abstrato. O fallback pro `initial_odometer` é o valor certo de um veículo sem
        viagem nenhuma — e um veículo com viagens nunca chega aqui."""

        return self._to_entity_with(row, row.initial_odometer)

    def _to_entity_with(self, row: VehicleModel, current_odometer: int) -> Vehicle:
        return Vehicle(
            id=row.id,
            organization_id=row.organization_id,
            plate=row.plate,
            brand=row.brand,
            model=row.model,
            model_year=row.model_year,
            initial_odometer=row.initial_odometer,
            status=row.status,
            created_at=row.created_at,
            current_odometer=current_odometer,
        )


class DriverRepository(
    TenantScopedRepository[
        DriverModel,
        Driver,
        DriverFilters,
        NewDriver,
        UpdateDriver,
    ]
):
    model = DriverModel
    filters_type = DriverFilters

    async def get_by_user_id(self, user_id: uuid.UUID) -> Driver | None:
        """O condutor vinculado a um login, **dentro da organização ativa**.

        É o que dá sentido ao `frota.usages.write_own`: "próprio" quer dizer o uso cujo
        `driver_id` aponta pra este condutor. Quem não tem condutor vinculado recebe `None`, e o
        use case traduz isso em 422 — ele não é condutor cadastrado, e a mensagem diz isso."""

        result = await self._session.execute(
            sa.select(DriverModel).where(
                DriverModel.user_id == user_id,
                DriverModel.organization_id == self.organization_id,
            )
        )
        row = result.scalars().one_or_none()
        return self._to_entity(row) if row else None

    async def create(self, create_command: NewDriver) -> Driver:
        try:
            return await super().create(create_command)
        except IntegrityError as exc:
            if _constraint_of(exc) == "uq_drivers_organization_user":
                raise ConflictError(
                    "Esta pessoa já está cadastrada como condutor nesta Empresa."
                ) from exc
            raise

    async def update(self, id_: uuid.UUID, update_command: UpdateDriver) -> Driver:
        try:
            return await super().update(id_, update_command)
        except IntegrityError as exc:
            if _constraint_of(exc) == "uq_drivers_organization_user":
                raise ConflictError(
                    "Esta pessoa já está cadastrada como condutor nesta Empresa."
                ) from exc
            raise

    async def labels(self) -> dict[uuid.UUID, str]:
        """`{id: nome}` de todos os condutores da Empresa — ver `VehicleRepository.labels`."""

        result = await self._session.execute(
            sa.select(DriverModel.id, DriverModel.name).where(self._tenant_filter)
        )
        return {id_: name for id_, name in result.all()}

    def _apply_filters(self, stmt: sa.Select, filters: DriverFilters) -> sa.Select:
        if filters.status is not None:
            stmt = stmt.where(DriverModel.status == filters.status)
        return stmt.order_by(DriverModel.name)

    def _to_entity(self, row: DriverModel) -> Driver:
        return Driver(
            id=row.id,
            organization_id=row.organization_id,
            name=row.name,
            user_id=row.user_id,
            license_number=row.license_number,
            license_category=row.license_category,
            license_expires_at=row.license_expires_at,
            status=row.status,
            created_at=row.created_at,
        )


_USAGE_CONFLICTS: dict[str, str] = {
    "ex_vehicle_usages_no_overlap": (
        "Este veículo já tem uma viagem registrada que se sobrepõe a este período."
    ),
    "ck_vehicle_usages_period": "A hora de volta tem que ser depois da hora de saída.",
    "ck_vehicle_usages_odometer": ("O hodômetro final não pode ser menor que o inicial."),
    "ck_vehicle_usages_closed_together": (
        "Encerrar uma viagem exige hora de volta e hodômetro final juntos."
    ),
    "fk_vehicle_usages_vehicle": "Veículo não encontrado nesta Empresa.",
    "fk_vehicle_usages_driver": "Condutor não encontrado nesta Empresa.",
    "fk_vehicle_usages_start_reading": "Leitura de hodômetro não encontrada nesta Empresa.",
    "fk_vehicle_usages_end_reading": "Leitura de hodômetro não encontrada nesta Empresa.",
}
"""Cada constraint de `vehicle_usages` com a frase que ela merece.

A da exclusão é a que importa mais: ela é traduzida de `IntegrityError` e **não** verificada com
um `SELECT` antes. Entre a leitura e a escrita cabe outro lançamento, e a corrida é justamente o
caso que a constraint existe pra pegar — mesma decisão do `UPDATE ... WHERE status = 'pending'`
da spec 06."""


class VehicleUsageRepository(
    TenantScopedRepository[
        VehicleUsageModel,
        VehicleUsage,
        VehicleUsageFilters,
        NewVehicleUsage,
        UpdateVehicleUsage,
    ]
):
    model = VehicleUsageModel
    filters_type = VehicleUsageFilters

    async def create(self, create_command: NewVehicleUsage) -> VehicleUsage:
        try:
            return await super().create(create_command)
        except IntegrityError as exc:
            raise self._as_conflict(exc) from exc

    async def update(self, id_: uuid.UUID, update_command: UpdateVehicleUsage) -> VehicleUsage:
        try:
            return await super().update(id_, update_command)
        except IntegrityError as exc:
            raise self._as_conflict(exc) from exc

    async def is_reading_referenced(self, reading_id: uuid.UUID) -> bool:
        """Se alguma viagem **já** aponta pra esta leitura, de qualquer um dos dois lados.

        Sem esta conferência, uma foto viraria evidência de duas viagens diferentes — e a
        evidência que serve pra duas viagens não serve pra nenhuma.

        É checagem de aplicação, e **não** um `UNIQUE` no banco, porque a regra é cruzada: a
        mesma leitura não pode ser nem saída de A nem chegada de B, e dois índices únicos (um por
        coluna) não expressariam isso. Um `UNIQUE` por coluna daria meia garantia e ainda exigiria
        este `SELECT`; fica um mecanismo só, e o custo é uma corrida estreita entre duas
        requisições simultâneas apontando a mesma foto. Ver `Como ficou` da spec 11."""

        result = await self._session.execute(
            sa.select(sa.literal(1))
            .select_from(VehicleUsageModel)
            .where(
                VehicleUsageModel.organization_id == self.organization_id,
                sa.or_(
                    VehicleUsageModel.start_reading_id == reading_id,
                    VehicleUsageModel.end_reading_id == reading_id,
                ),
            )
            .limit(1)
        )
        return result.first() is not None

    async def close_if_open(
        self,
        id_: uuid.UUID,
        ended_at: Any,
        end_odometer: int,
        end_reading_id: uuid.UUID | None = None,
    ) -> bool:
        """Encerra a viagem, e devolve se **esta** chamada foi quem a encerrou.

        É um `UPDATE ... WHERE ended_at IS NULL` condicional, e não um `read` seguido de `write`,
        pelo mesmo motivo do `mark_accepted_if_pending` da spec 06: dois encerramentos
        simultâneos passariam os dois pela checagem e o segundo sobrescreveria o primeiro em
        silêncio. Aqui o segundo recebe `False`, e a rota responde 409 — o banco decide quem
        chegou primeiro."""

        values: dict[str, Any] = {"ended_at": ended_at, "end_odometer": end_odometer}
        if end_reading_id is not None:
            # Só entra no `SET` quando veio: encerrar sem foto não pode apagar uma que já
            # estivesse lá.
            values["end_reading_id"] = end_reading_id

        stmt = (
            sa.update(VehicleUsageModel)
            .where(
                VehicleUsageModel.id == id_,
                VehicleUsageModel.organization_id == self.organization_id,
                VehicleUsageModel.ended_at.is_(None),
            )
            .values(**values)
        )

        try:
            # `execute` é tipado como `Result[Any]`, que não conhece `rowcount`; um `UPDATE`
            # sempre devolve um `CursorResult`, e é dele que sai a contagem de linhas afetadas.
            # Mesmo `cast` do `mark_accepted_if_pending` do `access` (spec 06).
            result = cast(CursorResult[Any], await self._session.execute(stmt))
        except IntegrityError as exc:
            raise self._as_conflict(exc) from exc

        return bool(result.rowcount)

    async def list_for_report(
        self,
        started_from: Any,
        started_until: Any,
    ) -> list[UsageForReport]:
        """Os usos do período, no recorte mínimo que o relatório precisa.

        Não reusa `paginate` de propósito: relatório não é página, e trazer a entidade inteira
        (com `notes`, `purpose`, timestamps) pra somar dois inteiros seria desperdício num
        período de meses."""

        result = await self._session.execute(
            sa.select(
                VehicleUsageModel.vehicle_id,
                VehicleUsageModel.driver_id,
                VehicleUsageModel.start_odometer,
                VehicleUsageModel.end_odometer,
            ).where(
                VehicleUsageModel.organization_id == self.organization_id,
                VehicleUsageModel.started_at >= started_from,
                VehicleUsageModel.started_at <= started_until,
            )
        )

        return [
            UsageForReport(
                vehicle_id=vehicle_id,
                driver_id=driver_id,
                start_odometer=start_odometer,
                end_odometer=end_odometer,
            )
            for vehicle_id, driver_id, start_odometer, end_odometer in result.all()
        ]

    def _as_conflict(self, exc: IntegrityError) -> ConflictError:
        constraint = _constraint_of(exc)
        return ConflictError(
            _USAGE_CONFLICTS.get(constraint or "", "Não foi possível registrar este uso.")
        )

    def _apply_filters(self, stmt: sa.Select, filters: VehicleUsageFilters) -> sa.Select:
        if filters.vehicle_id is not None:
            stmt = stmt.where(VehicleUsageModel.vehicle_id == filters.vehicle_id)
        if filters.driver_id is not None:
            stmt = stmt.where(VehicleUsageModel.driver_id == filters.driver_id)
        if filters.started_from is not None:
            stmt = stmt.where(VehicleUsageModel.started_at >= filters.started_from)
        if filters.started_until is not None:
            stmt = stmt.where(VehicleUsageModel.started_at <= filters.started_until)
        if filters.only_open:
            stmt = stmt.where(VehicleUsageModel.ended_at.is_(None))
        return stmt.order_by(VehicleUsageModel.started_at.desc())

    def _to_entity(self, row: VehicleUsageModel) -> VehicleUsage:
        return VehicleUsage(
            id=row.id,
            organization_id=row.organization_id,
            vehicle_id=row.vehicle_id,
            driver_id=row.driver_id,
            started_at=row.started_at,
            ended_at=row.ended_at,
            start_odometer=row.start_odometer,
            end_odometer=row.end_odometer,
            purpose=row.purpose,
            notes=row.notes,
            created_by=row.created_by,
            created_at=row.created_at,
            start_reading_id=row.start_reading_id,
            end_reading_id=row.end_reading_id,
        )


class OdometerReadingRepository(
    TenantScopedRepository[
        OdometerReadingModel,
        OdometerReading,
        OdometerReadingFilters,
        NewOdometerReading,
        UpdateOdometerReading,
    ]
):
    """As leituras de hodômetro da Empresa ativa.

    Note o que **não** tem aqui: `update`. Uma leitura é o que a máquina disse, e o que a máquina
    disse não se corrige — a correção humana vira `start_odometer`/`end_odometer` na viagem, do
    outro lado. Sobrescrever `value_read` apagaria a única medida de erro do motor em produção."""

    model = OdometerReadingModel
    filters_type = OdometerReadingFilters

    async def count_by_user_since(self, user_id: uuid.UUID, since: datetime) -> int:
        """Quantas leituras esta pessoa fez nesta Empresa desde `since` — o teto de 30/hora.

        Por autor e não por organização: o limite existe pra conter um dedo travado no botão (ou
        um script), não pra racionar a Empresa. Um teto por tenant faria o segundo motorista do
        dia pagar pelo primeiro."""

        total = await self._session.scalar(
            sa.select(sa.func.count())
            .select_from(OdometerReadingModel)
            .where(
                OdometerReadingModel.organization_id == self.organization_id,
                OdometerReadingModel.created_by == user_id,
                OdometerReadingModel.created_at >= since,
            )
        )
        return total or 0

    async def list_orphans(self, older_than: datetime, limit: int) -> list[OdometerReading]:
        """Leituras velhas que nenhuma viagem aponta — lixo com foto junto.

        É a pessoa que fotografou e fechou o diálogo. `NOT EXISTS` contra as duas colunas de
        `vehicle_usages`, porque a referência mora **na viagem**: órfã é leitura que ninguém
        aponta."""

        apontada = (
            sa.select(sa.literal(1))
            .select_from(VehicleUsageModel)
            .where(
                sa.or_(
                    VehicleUsageModel.start_reading_id == OdometerReadingModel.id,
                    VehicleUsageModel.end_reading_id == OdometerReadingModel.id,
                )
            )
            .exists()
        )

        result = await self._session.execute(
            sa.select(OdometerReadingModel)
            .where(
                OdometerReadingModel.organization_id == self.organization_id,
                OdometerReadingModel.created_at < older_than,
                ~apontada,
            )
            .order_by(OdometerReadingModel.created_at)
            .limit(limit)
        )
        return [self._to_entity(row) for row in result.scalars().all()]

    async def delete_many(self, ids: Sequence[uuid.UUID]) -> None:
        if not ids:
            return

        await self._session.execute(
            sa.delete(OdometerReadingModel).where(
                OdometerReadingModel.id.in_(ids),
                OdometerReadingModel.organization_id == self.organization_id,
            )
        )

    def _apply_filters(self, stmt: sa.Select, filters: OdometerReadingFilters) -> sa.Select:
        if filters.vehicle_id is not None:
            stmt = stmt.where(OdometerReadingModel.vehicle_id == filters.vehicle_id)
        return stmt.order_by(OdometerReadingModel.created_at.desc())

    def _to_entity(self, row: OdometerReadingModel) -> OdometerReading:
        return OdometerReading(
            id=row.id,
            organization_id=row.organization_id,
            vehicle_id=row.vehicle_id,
            storage_key=row.storage_key,
            value_read=row.value_read,
            confidence=row.confidence,
            engine=row.engine,
            created_by=row.created_by,
            created_at=row.created_at,
        )
