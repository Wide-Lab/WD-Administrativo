import uuid
from dataclasses import dataclass

from src.core.tenancy import OrganizationType
from src.modules.access.domain.entities import AgreementStatus, MembershipStatus, Role


@dataclass(frozen=True, slots=True)
class CreateOrganizationCommand:
    """Provisiona um tenant. `type` entra aqui e nunca mais muda."""

    type: OrganizationType
    name: str
    document: str | None = None


@dataclass(frozen=True, slots=True)
class CreateAgreementCommand:
    """Vincula um Parceiro à Empresa ativa. A Empresa é a organização do path — não vem no
    corpo, senão daria pra conveniar em nome de outra."""

    partner_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class UpdateAgreementStatusCommand:
    status: AgreementStatus


@dataclass(frozen=True, slots=True)
class UpdateMembershipCommand:
    """Muda papel e/ou status de um membro. Os dois são opcionais e ao menos um é exigido —
    `None` aqui é "não mexe", não "apaga"."""

    role: Role | None = None
    status: MembershipStatus | None = None


@dataclass(frozen=True, slots=True)
class CreateInvitationCommand:
    """Convida alguém pra organização ativa, com o papel já decidido.

    A organização não vem aqui pelo mesmo motivo do convênio: é a do path. Aceitá-la no corpo
    abriria convidar pra organização alheia — que é o critério 4 da spec 06."""

    email: str
    role: Role


@dataclass(frozen=True, slots=True)
class AcceptInvitationCommand:
    """O aceite. `name` é opcional porque quem já tem conta já tem nome — e, nesse caso, nem o
    nome nem a senha daqui são usados: o convite só cria o vínculo. Ver o use case."""

    token: str
    password: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterPartnerCommand:
    """O auto-cadastro de Parceiro: a organização e o primeiro admin nascem juntos.

    `company_name` é o nome do **Parceiro**, não de uma Empresa — o nome do campo é o que a
    spec 06 fixou no payload. Ver `Como ficou`."""

    company_name: str
    admin_name: str
    admin_email: str
    admin_password: str
    document: str | None = None
