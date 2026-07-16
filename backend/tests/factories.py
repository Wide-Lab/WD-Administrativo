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
from datetime import UTC, datetime, timedelta

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
