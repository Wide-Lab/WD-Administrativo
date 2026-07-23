import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.session import SessionDep

type UserId = uuid.UUID


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Identidade global de quem fez a requisição. Só identidade: sem organização, sem papel
    e sem permissão — isso muda a cada request e é resolvido pelo `access` (specs 04/05)."""

    id: UserId
    email: str
    name: str


@dataclass(frozen=True, slots=True)
class UserProfile:
    """A identidade de **alguém**, e não de quem pergunta.

    Tem os mesmos três campos de `CurrentUser` e mesmo assim é um tipo separado, porque a
    pergunta é outra: `CurrentUser` é o sujeito da requisição — o que `require_permission`
    autoriza e o que a sessão carrega —, e um `UserProfile` é um terceiro, exibido numa lista.
    Fundir os dois faria `CurrentUser` circular por listagens onde ninguém está autenticado como
    aquela pessoa, e o primeiro `if user.id == ...` escrito por engano viraria um bug de
    autorização."""

    id: UserId
    email: str
    name: str


class UserReader(Protocol):
    """Porta de leitura de identidade. Existe para o `core` resolver `current_user` sem
    importar `auth` — quem a implementa é o módulo `auth`, que é dono da tabela `users`."""

    async def get_active_by_id(self, user_id: UserId) -> CurrentUser | None: ...

    async def list_profiles_by_ids(
        self,
        user_ids: Sequence[UserId],
    ) -> Mapping[UserId, UserProfile]:
        """Traduz ids de usuário em nome e e-mail, **em lote**.

        Existe porque a lista de membros do `access` mostra pessoas, e `memberships` só guarda
        o id — a tabela `users` é do `auth`. Sem esta porta, `access` importaria `auth` para
        pintar uma coluna, e o seam de extração cairia por um `<td>`. Mesmo motivo do
        `UserDirectory`, e para o terceiro verbo.

        **Em lote, e não um `get` por linha**, porque quem chama tem uma página inteira na mão:
        a versão singular convidaria ao N+1 sem que nada no tipo denunciasse. Recebe uma
        `Sequence` porque a ordem de quem pergunta é dele; devolve um `Mapping` porque quem
        responde não sabe em que ordem exibir.

        Devolve o perfil de quem foi **desativado** também — diferente do `get_active_by_id`,
        que filtra por `active` de propósito. São perguntas opostas: lá se decide se alguém
        entra, aqui se mostra quem é o dono de um vínculo que existe. Esconder o nome de um
        usuário desativado faria a linha dele voltar a ser um UUID justamente na tela que serve
        pra reativá-lo.

        Um id sem linha correspondente simplesmente **não aparece** no mapa — quem chama decide
        o que isso significa no contexto dele.
        """

        ...


class UserDirectory(Protocol):
    """Porta de **escrita** de identidade: criar a pessoa que ainda não tem login.

    Existe pelo mesmo motivo que o `UserReader`, e para o outro lado do verbo. O onboarding
    (spec 06) é de `access` — é ele que sabe que um convite aceito vira vínculo —, mas a
    tabela `users` é do `auth`. Sem esta porta, `access` importaria `auth` para criar o
    usuário do convidado, e o seam de extração cairia no primeiro fluxo de entrada de gente.

    `create` recebe a senha **em claro**, e não um hash: quem decide como uma senha é guardada
    é o dono da identidade. Um `CentralSsoUserDirectory` futuro recusaria a senha em vez de
    hasheá-la, e o `access` não precisaria saber da diferença."""

    async def find_id_by_email(self, email: str) -> UserId | None: ...

    async def create(self, email: str, name: str, password: str) -> UserId: ...


class Authenticator[CredentialsT](Protocol):
    """Porta de autenticação: troca credenciais por uma identidade local.

    `PasswordAuthenticator` (spec 02) confere a senha na tabela `users`. Ligar "entrar com a
    Widelab" no futuro é somar um `CentralSsoAuthenticator` que valida o JWT da Central e
    mapeia pro usuário local — sem tocar em nada de `access`/autorização."""

    async def authenticate(self, credentials: CredentialsT) -> UserId: ...


type UserReaderFactory = Callable[[AsyncSession], UserReader]

_user_reader_factory: UserReaderFactory | None = None


def set_user_reader_factory(factory: UserReaderFactory) -> None:
    """Liga a implementação de `UserReader` ao `core`. Chamada uma vez em `mount_routes` pelo
    kernel — é o que mantém a seta de dependência apontando pra dentro (`core` nunca importa
    um módulo)."""

    global _user_reader_factory
    _user_reader_factory = factory


async def get_user_reader(session: SessionDep) -> UserReader:
    if _user_reader_factory is None:
        raise RuntimeError(
            "Nenhum UserReader registrado. O kernel `auth` deve chamar "
            "set_user_reader_factory() em mount_routes."
        )
    return _user_reader_factory(session)


UserReaderDep = Annotated[UserReader, Depends(get_user_reader)]


type UserDirectoryFactory = Callable[[AsyncSession], UserDirectory]

_user_directory_factory: UserDirectoryFactory | None = None


def set_user_directory_factory(factory: UserDirectoryFactory) -> None:
    """Liga a implementação de `UserDirectory` ao `core`. Chamada uma vez em `mount_routes`
    pelo `auth`, como a do `UserReader`."""

    global _user_directory_factory
    _user_directory_factory = factory


async def get_user_directory(session: SessionDep) -> UserDirectory:
    """A implementação registrada, sobre a **sessão da requisição**.

    Receber a mesma `SessionDep` que a unit of work de quem chama não é detalhe: é o que faz
    o auto-cadastro de Parceiro (spec 06) ser atômico. `organizations` é do `access` e `users`
    é do `auth`, mas os dois `INSERT` saem da mesma sessão — um `commit` só cobre os dois, e
    um e-mail duplicado desfaz a organização junto, sem deixar tenant órfão."""

    if _user_directory_factory is None:
        raise RuntimeError(
            "Nenhum UserDirectory registrado. O kernel `auth` deve chamar "
            "set_user_directory_factory() em mount_routes."
        )
    return _user_directory_factory(session)


UserDirectoryDep = Annotated[UserDirectory, Depends(get_user_directory)]
