import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError
from src.core.security import UserId, hash_password
from src.modules.auth.adapters.db.models import User as UserModel


class SqlAlchemyUserDirectory:
    """A implementação de `UserDirectory` — o `auth` entregando ao `core` o poder de criar
    identidade, pro `access` fazer onboarding sem importar este módulo.

    Não passa pela `UserRepository` nem pela unit of work do `auth` de propósito: a sessão
    aqui é a **de quem chama** (o onboarding do `access`), e é isso que põe o `INSERT` de
    `users` na mesma transação do `INSERT` de `organizations`. Uma uow própria abriria uma
    segunda transação, e o auto-cadastro deixaria de ser atômico — que é o critério 3 da
    spec 06."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_id_by_email(self, email: str) -> UserId | None:
        """O id de quem já tem login, ou `None`. Comparação case-insensitive de graça: a
        coluna é CITEXT, então não há `.lower()` aqui."""

        result = await self._session.execute(
            sa.select(UserModel.id).where(UserModel.email == email)
        )
        return result.scalars().one_or_none()

    async def create(self, email: str, name: str, password: str) -> UserId:
        """Cria a identidade e define a senha. O `commit` é de quem chama.

        A tradução de `IntegrityError` acontece aqui e não só no `commit` da uow porque o
        `flush` abaixo já manda o `INSERT`: sem ela, um e-mail duplicado no auto-cadastro
        viraria 500 em vez de 409. É o mesmo furo que a spec 03 registrou no `UserRepository`
        e não corrigiu por ser escopo do `auth` — a spec 06 traz o caso que o expõe, então o
        conserto entra pelo caminho novo."""

        model = UserModel(
            email=email,
            name=name,
            password_hash=hash_password(password),
        )
        self._session.add(model)

        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Já existe uma conta com este e-mail.") from exc

        return model.id
