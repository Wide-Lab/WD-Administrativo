"""Criação de usuário fora de fluxo.

Existe pro bootstrap do primeiro `platform_admin`, que não tem quem o convide. O vínculo com
a organização plataforma é dado pelas specs 03/04.

    python -m src.modules.auth.cli create-user --email … --name …
"""

import argparse
import asyncio
import getpass
import sys

from src.core.database.startup import get_database
from src.core.security import hash_password
from src.modules.auth.adapters.db.unit_of_work import AuthUnitOfWork
from src.modules.auth.domain.entities import NewUser, UserStatus

MIN_PASSWORD_LENGTH = 8


def _prompt_password() -> str:
    """Pede a senha duas vezes, sem eco. A senha não vem por argumento justamente pra não
    ficar no histórico do shell nem na lista de processos."""

    password = getpass.getpass("Senha: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"A senha precisa ter ao menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password != getpass.getpass("Confirme a senha: "):
        raise SystemExit("As senhas não conferem.")
    return password


async def _create_user(email: str, name: str, password: str) -> None:
    database = get_database()
    try:
        async with AuthUnitOfWork(session=database.create_session()) as uow:
            if await uow.users.get_credentials_by_email(email) is not None:
                raise SystemExit(f"Já existe um usuário com o e-mail {email}.")

            user = await uow.users.create(
                NewUser(
                    email=email,
                    name=name,
                    password_hash=hash_password(password),
                    status=UserStatus.ACTIVE,
                )
            )
            await uow.commit()
            print(f"Usuário criado: {user.id} <{user.email}>")
    finally:
        await database.dispose_engine()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m src.modules.auth.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create-user", help="Cria um usuário e pede a senha.")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)

    args = parser.parse_args(argv)
    asyncio.run(_create_user(email=args.email, name=args.name, password=_prompt_password()))


if __name__ == "__main__":
    main(sys.argv[1:])
