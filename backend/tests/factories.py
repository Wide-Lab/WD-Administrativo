"""As factories da suíte: o setup que todo teste de integração precisa, sem repetição.

Elas escrevem pelos **models**, e não pelas rotas, de propósito: montar o cenário de um teste de
403 não pode depender das rotas que o próprio teste está pondo em dúvida. Quem escreve pela API
é o teste que **testa** a API.

Note que nenhuma delas mente o `organization_type` de um vínculo: quem quiser mentir escreve o
`INSERT` na mão, e o teste que faz isso é justamente o que prova que o banco recusa
(`test_authz.py`)."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.modules import ModuleKey
from src.core.security import hash_password
from src.core.tenancy import OrganizationType
from src.modules.access.adapters.db.models import Invitation as InvitationModel
from src.modules.access.adapters.db.models import Membership as MembershipModel
from src.modules.access.adapters.db.models import ModuleEntitlement as ModuleEntitlementModel
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.adapters.db.models import PartnerAgreement as PartnerAgreementModel
from src.modules.access.domain.entities import (
    AgreementStatus,
    InvitationStatus,
    MembershipStatus,
    OrganizationStatus,
    Role,
)
from src.modules.auth.adapters.db.models import User as UserModel
from src.modules.auth.domain.entities import UserStatus
from src.modules.frota.adapters.db.models import Driver as DriverModel
from src.modules.frota.adapters.db.models import OdometerReading as OdometerReadingModel
from src.modules.frota.adapters.db.models import Vehicle as VehicleModel
from src.modules.frota.adapters.db.models import VehicleUsage as VehicleUsageModel
from src.modules.frota.domain.entities import DriverStatus, ReadingConfidence, VehicleStatus

DEFAULT_PASSWORD = "senha-de-teste-123"
"""A senha de quem a factory cria. Oito caracteres ou mais — a política do `PUT /api/me/password`
vale no aceite de convite e no cadastro de Parceiro, e uma senha curta aqui faria testes falharem
por 422 e não pelo que eles perguntam."""

INVITATION_TTL_DAYS = 7


@dataclass(frozen=True, slots=True)
class CreatedUser:
    """O usuário criado, **com a senha em claro** junto.

    O hash é o que vai pro banco; a senha em claro fica aqui porque o login da fixture `como` é
    de verdade, e ele precisa dela. É o único lugar da suíte que as duas pontas se encontram."""

    id: uuid.UUID
    email: str
    name: str
    password: str | None


def unique_email(prefix: str = "pessoa") -> str:
    """Um e-mail que não colide com o de outro teste. O `TRUNCATE` entre testes já garantiria
    isso; o sufixo aleatório garante dentro do **mesmo** teste, que cria várias pessoas."""

    return f"{prefix}-{uuid.uuid4().hex[:12]}@teste.widelab"


async def make_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    name: str | None = None,
    password: str | None = DEFAULT_PASSWORD,
    status: UserStatus = UserStatus.ACTIVE,
) -> CreatedUser:
    """Uma identidade global. `password=None` é o convidado que ainda não definiu senha."""

    email = email or unique_email()
    name = name or "Pessoa de Teste"

    user = UserModel(
        email=email,
        name=name,
        password_hash=hash_password(password) if password is not None else None,
        status=status,
    )
    session.add(user)
    await session.commit()

    return CreatedUser(id=user.id, email=email, name=name, password=password)


async def make_organization(
    session: AsyncSession,
    *,
    type: OrganizationType,
    name: str | None = None,
    document: str | None = None,
    status: OrganizationStatus = OrganizationStatus.ACTIVE,
) -> OrganizationModel:
    organization = OrganizationModel(
        type=type,
        name=name or f"Organização {uuid.uuid4().hex[:6]}",
        document=document,
        status=status,
    )
    session.add(organization)
    await session.commit()

    return organization


async def make_company(
    session: AsyncSession,
    *,
    name: str | None = None,
    document: str | None = None,
    status: OrganizationStatus = OrganizationStatus.ACTIVE,
) -> OrganizationModel:
    """Uma Empresa — o tenant que contrata módulo e convida gente."""

    return await make_organization(
        session,
        type=OrganizationType.COMPANY,
        name=name or f"Empresa {uuid.uuid4().hex[:6]}",
        document=document,
        status=status,
    )


async def make_partner(
    session: AsyncSession,
    *,
    name: str | None = None,
    document: str | None = None,
    status: OrganizationStatus = OrganizationStatus.ACTIVE,
) -> OrganizationModel:
    """Um Parceiro — organização de primeiro nível, atende N Empresas."""

    return await make_organization(
        session,
        type=OrganizationType.PARTNER,
        name=name or f"Parceiro {uuid.uuid4().hex[:6]}",
        document=document,
        status=status,
    )


async def get_platform_organization(session: AsyncSession) -> OrganizationModel:
    """A organização `platform` semeada pela migration `0002` — o alvo do `platform_admin`.

    Não é factory: ninguém a cria. Existe exatamente uma, e o índice único parcial do banco
    recusaria a segunda."""

    result = await session.execute(
        sa.select(OrganizationModel).where(OrganizationModel.type == OrganizationType.PLATFORM)
    )
    return result.scalars().one()


async def make_membership(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    organization: OrganizationModel,
    role: Role,
    status: MembershipStatus = MembershipStatus.ACTIVE,
) -> MembershipModel:
    """O vínculo usuário↔organização↔papel.

    O `organization_type` sai da organização de verdade, e não de um parâmetro: a factory não
    oferece o caminho de mentir. Ver o docstring do módulo."""

    membership = MembershipModel(
        user_id=user_id,
        organization_id=organization.id,
        organization_type=organization.type,
        role=role,
        status=status,
    )
    session.add(membership)
    await session.commit()

    return membership


async def make_agreement(
    session: AsyncSession,
    *,
    company: OrganizationModel,
    partner: OrganizationModel,
    status: AgreementStatus = AgreementStatus.ACTIVE,
) -> PartnerAgreementModel:
    agreement = PartnerAgreementModel(
        company_id=company.id,
        partner_id=partner.id,
        status=status,
    )
    session.add(agreement)
    await session.commit()

    return agreement


async def make_entitlement(
    session: AsyncSession,
    *,
    organization: OrganizationModel,
    module_key: ModuleKey,
    granted_by: uuid.UUID,
) -> ModuleEntitlementModel:
    """ "Esta Empresa contratou este módulo" — a linha cuja **presença** é o sim."""

    entitlement = ModuleEntitlementModel(
        organization_id=organization.id,
        module_key=module_key,
        granted_by=granted_by,
    )
    session.add(entitlement)
    await session.commit()

    return entitlement


def unique_plate() -> str:
    """Uma placa que não colide com a de outro teste — o `UNIQUE (organization_id, plate)` é
    justamente o que vários deles põem à prova."""

    return f"T{uuid.uuid4().hex[:6].upper()}"


async def make_vehicle(
    session: AsyncSession,
    *,
    organization: OrganizationModel,
    plate: str | None = None,
    brand: str = "Fiat",
    model: str = "Strada",
    model_year: int | None = 2022,
    initial_odometer: int = 0,
    status: VehicleStatus = VehicleStatus.ACTIVE,
) -> VehicleModel:
    """Um veículo da frota. Note que a factory **não** normaliza a placa: quem a normaliza é a
    aplicação, e um teste que escreva por aqui está montando cenário, não exercitando a regra."""

    vehicle = VehicleModel(
        organization_id=organization.id,
        plate=plate or unique_plate(),
        brand=brand,
        model=model,
        model_year=model_year,
        initial_odometer=initial_odometer,
        status=status,
    )
    session.add(vehicle)
    await session.commit()

    return vehicle


async def make_driver(
    session: AsyncSession,
    *,
    organization: OrganizationModel,
    name: str | None = None,
    user_id: uuid.UUID | None = None,
    license_number: str | None = None,
    license_category: str | None = None,
    license_expires_at: date | None = None,
    status: DriverStatus = DriverStatus.ACTIVE,
) -> DriverModel:
    """Um condutor. `user_id=None` é o motorista terceirizado, que dirige e nunca loga — o caso
    comum; passar um `user_id` é o que habilita o `frota.usages.write_own` daquela pessoa."""

    driver = DriverModel(
        organization_id=organization.id,
        name=name or f"Condutor {uuid.uuid4().hex[:6]}",
        user_id=user_id,
        license_number=license_number,
        license_category=license_category,
        license_expires_at=license_expires_at,
        status=status,
    )
    session.add(driver)
    await session.commit()

    return driver


async def make_usage(
    session: AsyncSession,
    *,
    organization: OrganizationModel,
    vehicle: VehicleModel,
    driver: DriverModel,
    created_by: uuid.UUID,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    start_odometer: int = 1000,
    end_odometer: int | None = None,
    purpose: str | None = None,
    notes: str | None = None,
) -> VehicleUsageModel:
    """Uma viagem registrada. Sem `ended_at`, nasce **aberta** — e uma viagem aberta colide com
    qualquer outra do mesmo veículo, pela constraint de exclusão."""

    usage = VehicleUsageModel(
        organization_id=organization.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        started_at=started_at or (datetime.now(UTC) - timedelta(days=1)),
        ended_at=ended_at,
        start_odometer=start_odometer,
        end_odometer=end_odometer,
        purpose=purpose,
        notes=notes,
        created_by=created_by,
    )
    session.add(usage)
    await session.commit()

    return usage


async def make_reading(
    session: AsyncSession,
    *,
    organization: OrganizationModel,
    vehicle: VehicleModel,
    created_by: uuid.UUID,
    storage_key: str | None = None,
    value_read: int | None = 45_210,
    confidence: ReadingConfidence = ReadingConfidence.HIGH,
    engine: str = "stub",
    created_at: datetime | None = None,
) -> OdometerReadingModel:
    """Uma leitura de hodômetro já gravada.

    `created_at` é parâmetro porque a purga de órfãs mede **idade**: sem poder plantar uma leitura
    de 25 horas atrás, o critério 12 não teria como ser testado sem esperar um dia.

    A factory escreve só a linha, **não o objeto** — quem quiser conferir os dois lados põe a foto
    no storage do teste. É o mesmo princípio das outras: montar cenário não passa pela rota que o
    teste põe em dúvida."""

    reading = OdometerReadingModel(
        id=uuid.uuid7(),
        organization_id=organization.id,
        vehicle_id=vehicle.id,
        storage_key=storage_key or f"{organization.id}/frota/hodometro/{uuid.uuid4()}.jpg",
        value_read=value_read,
        confidence=confidence,
        engine=engine,
        created_by=created_by,
    )
    if created_at is not None:
        reading.created_at = created_at

    session.add(reading)
    await session.commit()

    return reading


async def make_invitation(
    session: AsyncSession,
    *,
    organization: OrganizationModel,
    role: Role,
    invited_by: uuid.UUID,
    email: str | None = None,
    token: str | None = None,
    status: InvitationStatus = InvitationStatus.PENDING,
    expires_at: datetime | None = None,
) -> InvitationModel:
    """Um convite. `expires_at` no passado é o atalho pro teste de TTL — a expiração é derivada
    de `expires_at`, e `status='expired'` nunca é gravado."""

    invitation = InvitationModel(
        email=email or unique_email("convidado"),
        organization_id=organization.id,
        organization_type=organization.type,
        role=role,
        token=token or secrets.token_urlsafe(32),
        status=status,
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS),
        invited_by=invited_by,
    )
    session.add(invitation)
    await session.commit()

    return invitation
