"""A aba Membros pelo lado do backend: quem a lista **mostra**, e o que ela recusa mexer.

Dois assuntos que chegaram juntos porque nascem do mesmo lugar — a `MemberResponse` devolvia só
o `user_id` (a tela exibia UUID) e o `PATCH` não guardava nada contra auto-rebaixamento (um
`company_admin` se rebaixava e deixava a organização sem quem a administre). Ver o `Como ficou`
da `backend/04`."""

import uuid
from typing import Any

import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Membership as MembershipModel
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import MembershipStatus, Role
from src.modules.auth.domain.entities import UserStatus
from tests.conftest import Como
from tests.factories import make_company, make_membership, make_partner, make_user, unique_email


async def _meu_vinculo(client: AsyncClient, org_id: uuid.UUID, email: str) -> dict[str, Any]:
    """O meu membro, achado pelo e-mail na própria listagem.

    Achar pelo e-mail só é possível **porque** a listagem passou a devolvê-lo, então este helper
    é, ele mesmo, meio teste: se a coluna voltar a ser só o id, todo teste de auto-edição daqui
    quebra junto — e é isso que se quer, porque os dois assuntos são o mesmo vínculo."""

    response = await client.get(f"/api/organizacoes/{org_id}/membros")
    assert response.status_code == 200

    meus = [item for item in response.json()["items"] if item["email"] == email]
    assert len(meus) == 1, f"esperava exatamente um vínculo com {email}, achei {len(meus)}"

    return meus[0]


async def test_a_listagem_devolve_nome_e_email_e_nao_so_o_id(
    session: AsyncSession,
    como: Como,
) -> None:
    """O que a tela precisa pra escrever "Ana Torres" em vez de um UUID.

    Note de onde isso vem: não há join nenhum — `memberships` é do `access` e `users` é do
    `auth`. Quem cruza é o use case, pela porta `UserReader` do `core`."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    ana = await make_user(session, name="Ana Torres", email=unique_email("ana"))
    await make_membership(session, user_id=ana.id, organization=acme, role=Role.COLLABORATOR)

    response = await admin.get(f"/api/organizacoes/{acme.id}/membros")

    assert response.status_code == 200
    dela = next(item for item in response.json()["items"] if item["user_id"] == str(ana.id))
    assert dela["name"] == "Ana Torres"
    assert dela["email"] == ana.email


async def test_a_listagem_mostra_tambem_quem_foi_desativado(
    session: AsyncSession,
    como: Como,
) -> None:
    """**O caso que o `get_active_by_id` erraria**, e a razão de a porta ter um método novo em
    vez de reusar aquele.

    São duas desativações diferentes e as duas caem aqui: a do **vínculo**
    (`memberships.status`) e a da **identidade** (`users.status`). Nenhuma das duas pode sumir
    com o nome da pessoa, porque esta é justamente a tela onde alguém decide reativá-la — e uma
    linha anônima é uma linha que ninguém tem coragem de mexer."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    demitido = await make_user(
        session,
        name="Bruno Sem Acesso",
        status=UserStatus.DISABLED,
    )
    await make_membership(
        session,
        user_id=demitido.id,
        organization=acme,
        role=Role.COLLABORATOR,
        status=MembershipStatus.DISABLED,
    )

    response = await admin.get(f"/api/organizacoes/{acme.id}/membros")

    assert response.status_code == 200
    dele = next(item for item in response.json()["items"] if item["user_id"] == str(demitido.id))
    assert dele["name"] == "Bruno Sem Acesso"
    assert dele["email"] == demitido.email
    assert dele["status"] == "disabled"


async def test_o_patch_devolve_o_membro_com_a_identidade_junto(
    session: AsyncSession,
    como: Como,
) -> None:
    """A resposta do `PATCH` tem o mesmo formato da listagem.

    Se ela fosse mais pobre, a tela teria dois formatos do mesmo objeto pra parsear — e o
    membro recém-editado voltaria a ser um UUID até alguém recarregar a lista."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    ana = await make_user(session, name="Ana Torres")
    vinculo = await make_membership(
        session,
        user_id=ana.id,
        organization=acme,
        role=Role.COLLABORATOR,
    )

    response = await admin.patch(
        f"/api/organizacoes/{acme.id}/membros/{vinculo.id}",
        json={"role": "hr"},
    )

    assert response.status_code == 200
    corpo = response.json()
    assert corpo["role"] == "hr"
    assert corpo["name"] == "Ana Torres"
    assert corpo["email"] == ana.email


async def test_o_admin_nao_muda_o_proprio_papel(
    session: AsyncSession,
    como: Como,
) -> None:
    """**O buraco que esta entrega fechou**: um `company_admin` se rebaixava a `collaborator` e
    a organização ficava sem quem a administre — sem erro, e sem caminho de volta que não fosse
    a Widelab ou a CLI.

    422 e não 403: a permissão está lá (ele *tem* `members.write`), o que não existe é este
    ato."""

    acme = await make_company(session, name="Acme")
    email = unique_email("admin")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme, email=email)

    meu = await _meu_vinculo(admin, acme.id, email)

    response = await admin.patch(
        f"/api/organizacoes/{acme.id}/membros/{meu['id']}",
        json={"role": "collaborator"},
    )

    assert response.status_code == 422

    # E o banco não mudou: a recusa é antes do `update`, não um rollback depois dele.
    papel = await session.scalar(
        sa.select(MembershipModel.role).where(MembershipModel.id == uuid.UUID(meu["id"]))
    )
    assert papel == Role.COMPANY_ADMIN


async def test_o_admin_nao_desativa_o_proprio_vinculo(
    session: AsyncSession,
    como: Como,
) -> None:
    """O outro lado da mesma trava — e o estrago aqui é maior que o do rebaixamento: perder o
    papel tira capabilities, desativar o vínculo tira a organização inteira."""

    acme = await make_company(session, name="Acme")
    email = unique_email("admin")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme, email=email)

    meu = await _meu_vinculo(admin, acme.id, email)

    response = await admin.patch(
        f"/api/organizacoes/{acme.id}/membros/{meu['id']}",
        json={"status": "disabled"},
    )

    assert response.status_code == 422


async def test_a_trava_vale_para_o_partner_admin(
    session: AsyncSession,
    como: Como,
) -> None:
    """Não é regra de Empresa: `partner_admin` também tem `members.write`, e um Parceiro sem
    admin trava igual."""

    parceiro = await make_partner(session, name="Bom Prato")
    email = unique_email("parceiro")
    admin = await como(role=Role.PARTNER_ADMIN, org=parceiro, email=email)

    meu = await _meu_vinculo(admin, parceiro.id, email)

    response = await admin.patch(
        f"/api/organizacoes/{parceiro.id}/membros/{meu['id']}",
        json={"role": "partner_operator"},
    )

    assert response.status_code == 422


async def test_a_trava_vale_para_o_platform_admin_na_plataforma(
    como: Como,
    plataforma: OrganizationModel,
) -> None:
    """A Widelab é o caminho de volta de todo mundo — e é por isso que ela não é exceção aqui.

    Um `platform_admin` que se rebaixasse teria como caminho de volta apenas a CLI, que é
    exatamente o tipo de conserto que esta trava existe pra evitar."""

    email = unique_email("widelab")
    widelab = await como(role=Role.PLATFORM_ADMIN, email=email)

    meu = await _meu_vinculo(widelab, plataforma.id, email)

    response = await widelab.patch(
        f"/api/organizacoes/{plataforma.id}/membros/{meu['id']}",
        json={"status": "disabled"},
    )

    assert response.status_code == 422


async def test_o_admin_segue_editando_os_outros(
    session: AsyncSession,
    como: Como,
) -> None:
    """A trava é sobre a **própria** linha, e só. O par do teste acima: sem ele, "ninguém edita
    ninguém" passaria verde na suíte inteira.

    É esta assimetria que dispensa uma regra de "último administrador ativo": cada um só edita
    os outros, então sempre sobra pelo menos quem editou."""

    acme = await make_company(session, name="Acme")
    admin = await como(role=Role.COMPANY_ADMIN, org=acme)

    outro = await make_user(session)
    vinculo = await make_membership(
        session,
        user_id=outro.id,
        organization=acme,
        role=Role.COMPANY_ADMIN,
    )

    response = await admin.patch(
        f"/api/organizacoes/{acme.id}/membros/{vinculo.id}",
        json={"status": "disabled"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "disabled"
