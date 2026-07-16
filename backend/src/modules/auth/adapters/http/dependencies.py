from src.core.database.session import SessionDep
from src.modules.auth.adapters.authenticators.password import PasswordAuthenticator
from src.modules.auth.adapters.db.unit_of_work import AuthUnitOfWork


def get_unit_of_work(session: SessionDep) -> AuthUnitOfWork:
    """Embrulha a sessão da requisição numa unit of work, como a fundação prevê."""

    return AuthUnitOfWork(session=session)


def get_authenticator(session: SessionDep) -> PasswordAuthenticator:
    """A única linha que decide *como* alguém se autentica.

    Ligar o SSO da Central depois é trocar `PasswordAuthenticator` aqui: as rotas e os use
    cases falam com a porta `Authenticator`, nunca com a implementação."""

    return PasswordAuthenticator(uow=AuthUnitOfWork(session=session))
