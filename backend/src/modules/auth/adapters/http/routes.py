from fastapi import APIRouter, Response, status

from src.core.security import (
    CurrentUserDep,
    clear_session_cookie,
    issue_session,
    set_session_cookie,
)
from src.modules.auth.adapters.http.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
)
from src.modules.auth.adapters.http.types import AuthenticatorDep, UnitOfWorkDep
from src.modules.auth.application.dtos.commands import ChangePasswordCommand, LoginCommand
from src.modules.auth.application.use_cases.change_password import ChangePasswordUseCase
from src.modules.auth.application.use_cases.login import LoginUseCase

router = APIRouter(tags=["auth"])


@router.post("/auth/login")
async def login(
    body: LoginRequest,
    response: Response,
    authenticator: AuthenticatorDep,
) -> None:
    """Autentica um usuário e entrega a sessão num cookie httpOnly.

    Credenciais inválidas levantam `UnauthorizedError` antes daqui — 401 e nenhum cookie."""

    use_case = LoginUseCase(authenticator=authenticator)
    user_id = await use_case.execute(
        command=LoginCommand(
            email=body.email,
            password=body.password,
        ),
    )

    set_session_cookie(response, issue_session(user_id))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Encerra a sessão apagando o cookie."""

    clear_session_cookie(response=response)


@router.get("/me")
async def me(user: CurrentUserDep) -> MeResponse:
    """Identidade do usuário logado. 401 se não logado."""

    return MeResponse(
        id=user.id,
        email=user.email,
        name=user.name,
    )


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: CurrentUserDep,
    uow: UnitOfWorkDep,
) -> None:
    """Troca a senha do usuário logado, conferindo a senha atual."""

    use_case = ChangePasswordUseCase(uow=uow)
    await use_case.execute(
        user_id=user.id,
        command=ChangePasswordCommand(
            current_password=body.current_password,
            new_password=body.new_password,
        ),
    )
