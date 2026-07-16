"""Criação de vínculo fora de fluxo.

Existe pro bootstrap do primeiro `platform_admin` — a spec 02 deixou o vínculo com a
organização plataforma explicitamente pra cá ("O vínculo com a organização plataforma é dado
pela spec 03/04"). Sem isto, apertar o guard trancaria a porta com a chave dentro: nenhuma
rota cria vínculo (criar membro é convite, spec 06) e nenhuma rota de plataforma responde sem
um `platform_admin` já existir.

    python -m src.modules.access.cli grant --email … --role platform_admin
    python -m src.modules.access.cli grant --email … --role company_admin --org <uuid>
"""

import argparse
import asyncio
import sys
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.startup import get_database
from src.core.tenancy import OrganizationType
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.adapters.db.unit_of_work import AccessUnitOfWork
from src.modules.access.domain.entities import NewMembership, Role
from src.modules.access.domain.permissions import is_role_valid_for, roles_for


async def _resolve_user_id(session: AsyncSession, email: str) -> uuid.UUID:
    """Resolve o e-mail pelo `users` em SQL cru, de propósito: `access` não importa `auth`.

    A regra que vale é a de *import* entre módulos, e ela segue de pé — nenhuma classe do
    `auth` atravessa a fronteira. No banco os dois convivem no mesmo schema, e é a mesma
    licença que a FK `memberships.user_id → users.id` já usa."""

    result = await session.execute(
        sa.text("SELECT id FROM users WHERE email = :email").bindparams(email=email)
    )
    row = result.one_or_none()
    if row is None:
        raise SystemExit(f"Nenhum usuário com o e-mail {email}. Crie-o com o CLI do `auth`.")
    return uuid.UUID(str(row[0]))


async def _resolve_organization(
    session: AsyncSession,
    organization_id: uuid.UUID | None,
) -> OrganizationModel:
    """Sem `--org`, o alvo é a organização `platform` — o caso do bootstrap, e o único em que
    não há ambiguidade: existe exatamente uma."""

    stmt = sa.select(OrganizationModel)
    stmt = (
        stmt.where(OrganizationModel.id == organization_id)
        if organization_id is not None
        else stmt.where(OrganizationModel.type == OrganizationType.PLATFORM)
    )

    organization = (await session.execute(stmt)).scalars().one_or_none()
    if organization is None:
        raise SystemExit("Organização não encontrada.")
    return organization


async def _grant(email: str, role: Role, organization_id: uuid.UUID | None) -> None:
    database = get_database()
    session = database.create_session()
    try:
        async with AccessUnitOfWork(session=session) as uow:
            user_id = await _resolve_user_id(session, email)
            organization = await _resolve_organization(session, organization_id)

            if not is_role_valid_for(organization.type, role):
                valid = ", ".join(sorted(r.value for r in roles_for(organization.type)))
                raise SystemExit(
                    f"O papel '{role.value}' não existe numa organização do tipo "
                    f"'{organization.type.value}'. Papéis válidos: {valid}."
                )

            membership = await uow.memberships.create(
                NewMembership(
                    user_id=user_id,
                    organization_id=organization.id,
                    organization_type=organization.type,
                    role=role,
                )
            )
            await uow.commit()
            print(
                f"Vínculo criado: {membership.id} — {email} é {role.value} "
                f"em {organization.name} ({organization.type.value})."
            )
    finally:
        await database.dispose_engine()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m src.modules.access.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    grant = subparsers.add_parser("grant", help="Vincula um usuário a uma organização.")
    grant.add_argument("--email", required=True)
    grant.add_argument("--role", required=True, choices=[role.value for role in Role])
    grant.add_argument(
        "--org",
        default=None,
        help="Id da organização. Sem isto, a organização plataforma.",
    )

    args = parser.parse_args(argv)
    asyncio.run(
        _grant(
            email=args.email,
            role=Role(args.role),
            organization_id=uuid.UUID(args.org) if args.org else None,
        )
    )


if __name__ == "__main__":
    main(sys.argv[1:])
