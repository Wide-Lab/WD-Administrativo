"""Os aliases de dependency das rotas da frota.

Cada guard nomeia a **capability**, não o papel — a rota diz o que precisa poder fazer, e o
`grants` do descritor decide quem pode. Mudar quem cadastra veículo é editar um `frozenset` em
`domain/permissions.py`, não caçar rotas."""

from typing import Annotated

from fastapi import Depends

from src.core.authz import require_permission
from src.core.pagination.params import PageParams
from src.core.tenancy import CurrentOrganization
from src.modules.frota.adapters.db.unit_of_work import FrotaUnitOfWork
from src.modules.frota.adapters.http.dependencies import (
    get_odometer_reader,
    get_page_params,
    get_unit_of_work,
    require_usage_write,
)
from src.modules.frota.application.ports.odometer_reader import OdometerReader
from src.modules.frota.domain.permissions import FrotaPermissions

UnitOfWorkDep = Annotated[FrotaUnitOfWork, Depends(get_unit_of_work)]

PageParamsDep = Annotated[PageParams, Depends(get_page_params)]

OdometerReaderDep = Annotated[OdometerReader, Depends(get_odometer_reader)]
"""O motor de leitura. É por este `Depends` que a suíte injeta o stub — e é o que garante que
nenhum teste fala com a rede."""

VehicleReaderDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(FrotaPermissions.VEHICLES_READ)),
]
"""`company_admin`, `manager` e **`collaborator`** — este último porque ele precisa escolher o
carro pra lançar a viagem; sem isso o formulário não tem o que oferecer."""

VehicleWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(FrotaPermissions.VEHICLES_WRITE)),
]

DriverReaderDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(FrotaPermissions.DRIVERS_READ)),
]
"""Sem o `collaborator`: ele lança em nome de si mesmo, e a lista de condutores da Empresa não é
dele."""

DriverWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(FrotaPermissions.DRIVERS_WRITE)),
]

UsageReaderDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(FrotaPermissions.USAGES_READ)),
]
"""Só o **relatório** o usa como guard. O `GET /usos` não: lá a capability decide o *escopo* do
que volta, não se a porta abre."""

UsageWriterDep = Annotated[
    CurrentOrganization,
    Depends(require_permission(FrotaPermissions.USAGES_WRITE)),
]
"""Escrita **sobre qualquer condutor** — e é o guard do `DELETE`, que o `write_own` não alcança
de propósito: quem apaga a própria viagem apaga a evidência."""

AnyUsageWriterDep = Annotated[CurrentOrganization, Depends(require_usage_write)]
"""`write` **ou** `write_own`. De quem é o uso é decidido depois, no use case."""
