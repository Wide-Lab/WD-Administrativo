"""Os repositórios da frota.

Os três herdam de `TenantScopedRepository`: nascem amarrados à organização ativa e não têm
caminho que dispense o filtro de tenant. Um use case que esqueça o `organization_id` continua
correto — é o que a `03` pede quando diz "pra ninguém esquecer o filtro"."""

import uuid
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy import CursorResult
from sqlalchemy.exc import IntegrityError

from src.core.database.repositories.tenant_scoped import TenantScopedRepository
from src.core.exceptions import ConflictError
from src.modules.frota.adapters.db.models import Driver as DriverModel
from src.modules.frota.adapters.db.models import Vehicle as VehicleModel
from src.modules.frota.adapters.db.models import VehicleUsage as VehicleUsageModel
from src.modules.frota.application.dtos.filters import (
    DriverFilters,
    VehicleFilters,
    VehicleUsageFilters,
)
from src.modules.frota.domain.entities import (
    Driver,
    NewDriver,
    NewVehicle,
    NewVehicleUsage,
    UpdateDriver,
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

    async def create(self, create_command: NewVehicle) -> Vehicle:
        """Cadastra um veículo. A placa duplicada **na mesma Empresa** é recusada pelo `UNIQUE`,
        e é aqui que a violação vira 409.

        A tradução acontece no `flush` e não só no `commit` pelo motivo de sempre neste projeto:
        o `INSERT` sai daqui, então a constraint estoura antes — sem este `except`, uma placa
        repetida viraria 500."""

        try:
            return await super().create(create_command)
        except IntegrityError as exc:
            if _constraint_of(exc) == "uq_vehicles_organization_plate":
                raise ConflictError(
                    f"Já existe um veículo com a placa '{create_command.plate}' nesta Empresa."
                ) from exc
            raise

    async def update(self, id_: uuid.UUID, update_command: UpdateVehicle) -> Vehicle:
        try:
            return await super().update(id_, update_command)
        except IntegrityError as exc:
            if _constraint_of(exc) == "uq_vehicles_organization_plate":
                raise ConflictError("Já existe um veículo com esta placa nesta Empresa.") from exc
            raise

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

    async def close_if_open(
        self,
        id_: uuid.UUID,
        ended_at: Any,
        end_odometer: int,
    ) -> bool:
        """Encerra a viagem, e devolve se **esta** chamada foi quem a encerrou.

        É um `UPDATE ... WHERE ended_at IS NULL` condicional, e não um `read` seguido de `write`,
        pelo mesmo motivo do `mark_accepted_if_pending` da spec 06: dois encerramentos
        simultâneos passariam os dois pela checagem e o segundo sobrescreveria o primeiro em
        silêncio. Aqui o segundo recebe `False`, e a rota responde 409 — o banco decide quem
        chegou primeiro."""

        stmt = (
            sa.update(VehicleUsageModel)
            .where(
                VehicleUsageModel.id == id_,
                VehicleUsageModel.organization_id == self.organization_id,
                VehicleUsageModel.ended_at.is_(None),
            )
            .values(ended_at=ended_at, end_odometer=end_odometer)
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
        )
