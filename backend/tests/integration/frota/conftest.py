"""O cenário que quase todo teste de frota precisa: uma Empresa **com o módulo ligado**.

Sem o entitlement, toda rota daqui responde 403 — então um teste que queira falar de papel ou de
regra de negócio precisa passar dessa porta primeiro. A fixture `empresa_com_frota` é o atalho, e
o teste que quer justamente o 403 usa `empresa_sem_frota`."""

import io
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Protocol

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.storage import LocalDirectoryStorage
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from src.modules.auth.adapters.db.models import User as UserModel
from src.modules.frota.adapters.db.models import Driver as DriverModel
from src.modules.frota.adapters.odometer.stub import StubOdometerReader
from src.modules.frota.domain.entities import ReadingConfidence
from tests.conftest import Como
from tests.factories import (
    make_company,
    make_driver,
    make_entitlement,
    make_user,
    unique_email,
)


def foto_jpeg(*, largura: int = 64, altura: int = 48) -> bytes:
    """Um JPEG de verdade, gerado na hora.

    Gerado e não fixture binária no repo porque o que os testes precisam é que os bytes
    **decodifiquem** — nenhum deles olha o conteúdo da imagem, já que o motor é o stub. Um
    `.jpg` versionado seria peso morto com a mesma função."""

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (largura, altura), color=(20, 20, 20)).save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def storage(tmp_path: Path) -> Iterator[LocalDirectoryStorage]:
    """O `ObjectStorage` da app apontado pra um diretório do teste.

    **Nenhum teste desta suíte fala com MinIO nem com a AWS** — é a porta do `core` que garante,
    e é por isso que ela existe. O teste que quiser conferir o objeto olha o `tmp_path`."""

    from src.core.storage import get_object_storage
    from src.main import app

    local = LocalDirectoryStorage(tmp_path)
    app.dependency_overrides[get_object_storage] = lambda: local
    yield local
    app.dependency_overrides.pop(get_object_storage, None)


class Motor(Protocol):
    """O contrato da fixture `motor` — ver o docstring dela."""

    def __call__(
        self,
        *,
        value: int | None = None,
        confidence: ReadingConfidence | None = None,
    ) -> None: ...


@pytest.fixture
def motor() -> Iterator[Motor]:
    """`motor(value=45210)` → o `StubOdometerReader` instalado na app.

    **É esta fixture que garante que a suíte não fala com rede**, e é o motivo principal de a
    porta `OdometerReader` existir. Chamá-la com `value=None` é o caso da abstenção, que o
    critério 3 cobra: 201, `valor: null`, e a linha e a foto gravadas assim mesmo.

    Instalada por default com um valor fixo, pra o teste que não fala de leitura não precisar
    pensar nisso."""

    from src.main import app
    from src.modules.frota.adapters.http.dependencies import get_odometer_reader

    def _motor(
        *,
        value: int | None = None,
        confidence: ReadingConfidence | None = None,
    ) -> None:
        stub = StubOdometerReader(value=value, confidence=confidence, engine="stub:teste")
        app.dependency_overrides[get_odometer_reader] = lambda: stub

    _motor(value=45_210)
    yield _motor
    app.dependency_overrides.pop(get_odometer_reader, None)


@pytest.fixture
async def empresa_sem_frota(session: AsyncSession) -> OrganizationModel:
    """Uma Empresa que **não** contratou o módulo. É o estado default de todo tenant novo:
    negação por padrão, e é o que o critério 2 põe à prova."""

    return await make_company(session, name="Empresa Sem Frota")


@pytest.fixture
async def empresa(session: AsyncSession) -> AsyncIterator[OrganizationModel]:
    """Uma Empresa com o módulo `frota` habilitado.

    O entitlement é criado pela factory, e não pelo `PUT /modulos/frota`, pelo motivo do docstring
    de `tests/factories.py`: montar cenário não pode depender da rota que outro teste põe em
    dúvida. Quem exercita o `PUT` é o teste do critério 2."""

    company = await make_company(session, name="Empresa Com Frota")
    quem_ligou = await make_user(session)
    await make_entitlement(
        session,
        organization=company,
        module_key="frota",
        granted_by=quem_ligou.id,
    )
    yield company


class ComoCondutor(Protocol):
    """O contrato da fixture `como_condutor` — ver o docstring dela."""

    async def __call__(
        self,
        *,
        role: Role,
        org: OrganizationModel,
        name: str | None = None,
    ) -> tuple[AsyncClient, DriverModel]: ...


@pytest.fixture
async def como_condutor(como: Como, session: AsyncSession) -> ComoCondutor:
    """`como_condutor(role=Role.COLLABORATOR, org=empresa)` → o cliente logado **e** o condutor
    vinculado ao `user_id` dele.

    É o setup que o `frota.usages.write_own` inteiro depende: "próprio" quer dizer o uso cujo
    `driver_id` aponta pro condutor deste login. Sem esta fixture, cada teste de `write_own`
    repetiria criar usuário, descobrir o id e cadastrar o condutor.

    O `user_id` é descoberto pelo e-mail porque a `como` não devolve o usuário — ela devolve um
    cliente já logado, que é o que quase todo teste quer. Aqui a frota precisa do outro lado."""

    async def _como_condutor(
        *,
        role: Role,
        org: OrganizationModel,
        name: str | None = None,
    ) -> tuple[AsyncClient, DriverModel]:
        email = unique_email("condutor")
        cliente = await como(role=role, org=org, email=email)

        user = (
            (await session.execute(sa.select(UserModel).where(UserModel.email == email)))
            .scalars()
            .one()
        )

        driver = await make_driver(
            session,
            organization=org,
            user_id=user.id,
            name=name or "Condutor Logado",
        )
        return cliente, driver

    return _como_condutor


@pytest.fixture
def papel_gestor() -> Role:
    """`manager` é o papel de prova deste módulo, e a escolha é deliberada: ele sai de
    `PERMISSIONS_BY_ROLE` com `frozenset()` **vazio**, então todo 200 que ele tirar aqui só pode
    ter vindo do `grants` do descritor. Um `company_admin` faria os testes passarem por acidente,
    porque ele já tem capabilities de kernel."""

    return Role.MANAGER
