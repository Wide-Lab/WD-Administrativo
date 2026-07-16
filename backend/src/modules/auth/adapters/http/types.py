from typing import Annotated

from fastapi import Depends

from src.core.security import Authenticator
from src.modules.auth.adapters.db.unit_of_work import AuthUnitOfWork
from src.modules.auth.adapters.http.dependencies import get_authenticator, get_unit_of_work
from src.modules.auth.domain.entities import PasswordCredentials

UnitOfWorkDep = Annotated[
    AuthUnitOfWork,
    Depends(get_unit_of_work),
]

AuthenticatorDep = Annotated[
    Authenticator[PasswordCredentials],
    Depends(get_authenticator),
]
