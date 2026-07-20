"""Condutores: entidade própria, vínculo opcional com login, sem `DELETE`.

Critérios 3 e 10 da spec 10."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from tests.conftest import Como
from tests.factories import make_company, make_driver, make_user


class TestCadastro:
    async def test_o_gestor_cadastra(self, como: Como, empresa: OrganizationModel) -> None:
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/condutores",
            json={"name": "Ana Motorista", "license_category": "AB"},
        )

        assert resposta.status_code == 201
        assert resposta.json()["name"] == "Ana Motorista"
        assert resposta.json()["user_id"] is None

    async def test_condutor_sem_login_e_o_caso_comum(
        self, como: Como, empresa: OrganizationModel
    ) -> None:
        """O motorista terceirizado dirige e nunca vai logar. Exigir login de todo condutor
        forçaria usuário-fantasma, e o resultado seria dado sujo."""

        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/condutores",
            json={"name": "Terceirizado"},
        )

        assert resposta.status_code == 201

    async def test_condutor_com_login_guarda_o_user_id(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        pessoa = await make_user(session)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/condutores",
            json={"name": "Quem Loga", "user_id": str(pessoa.id)},
        )

        assert resposta.status_code == 201
        assert resposta.json()["user_id"] == str(pessoa.id)

    async def test_o_mesmo_user_id_duas_vezes_e_409(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """Um usuário é no máximo um condutor na mesma Empresa, senão "lançar a própria viagem"
        fica ambíguo — e o `write_own` não teria como resolver de quem é o uso."""

        pessoa = await make_user(session)
        gestor = await como(role=Role.MANAGER, org=empresa)
        rota = f"/api/organizacoes/{empresa.id}/frota/condutores"

        primeiro = await gestor.post(rota, json={"name": "A", "user_id": str(pessoa.id)})
        assert primeiro.status_code == 201

        segundo = await gestor.post(rota, json={"name": "B", "user_id": str(pessoa.id)})

        assert segundo.status_code == 409

    async def test_o_mesmo_user_id_em_outra_empresa_e_aceito(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        """O único é parcial e por `(organization_id, user_id)`: a mesma pessoa pode dirigir em
        duas Empresas."""

        pessoa = await make_user(session)
        outra = await make_company(session, name="Outra")

        await make_driver(session, organization=outra, user_id=pessoa.id)

        gestor = await como(role=Role.MANAGER, org=empresa)
        resposta = await gestor.post(
            f"/api/organizacoes/{empresa.id}/frota/condutores",
            json={"name": "Dirige Nos Dois", "user_id": str(pessoa.id)},
        )

        assert resposta.status_code == 201

    async def test_dois_condutores_sem_login_convivem(
        self, como: Como, empresa: OrganizationModel
    ) -> None:
        """O único é **parcial** (`WHERE user_id IS NOT NULL`) justamente por isso: a frota
        terceirizada inteira tem `user_id` nulo."""

        gestor = await como(role=Role.MANAGER, org=empresa)
        rota = f"/api/organizacoes/{empresa.id}/frota/condutores"

        assert (await gestor.post(rota, json={"name": "Um"})).status_code == 201
        assert (await gestor.post(rota, json={"name": "Dois"})).status_code == 201


class TestPermissao:
    """Critério 3: o `collaborator` não cadastra condutor — nem lê a lista."""

    async def test_o_collaborator_nao_cadastra(
        self, como: Como, empresa: OrganizationModel
    ) -> None:
        pessoa = await como(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.post(
            f"/api/organizacoes/{empresa.id}/frota/condutores", json={"name": "X"}
        )

        assert resposta.status_code == 403

    async def test_o_collaborator_nao_le_a_lista(
        self, como: Como, empresa: OrganizationModel
    ) -> None:
        """Ele lança em nome de si mesmo, e a lista de condutores da Empresa não é dele."""

        pessoa = await como(role=Role.COLLABORATOR, org=empresa)

        resposta = await pessoa.get(f"/api/organizacoes/{empresa.id}/frota/condutores")

        assert resposta.status_code == 403

    async def test_o_finance_nao_alcanca(self, como: Como, empresa: OrganizationModel) -> None:
        financeiro = await como(role=Role.FINANCE, org=empresa)

        resposta = await financeiro.get(f"/api/organizacoes/{empresa.id}/frota/condutores")

        assert resposta.status_code == 403


class TestEscopoDeTenant:
    async def test_condutor_de_outra_empresa_nao_aparece(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        outra = await make_company(session, name="Vizinha")
        await make_driver(session, organization=outra, name="Alheio")
        await make_driver(session, organization=empresa, name="Meu")

        gestor = await como(role=Role.MANAGER, org=empresa)
        itens = (await gestor.get(f"/api/organizacoes/{empresa.id}/frota/condutores")).json()[
            "items"
        ]

        assert [item["name"] for item in itens] == ["Meu"]

    async def test_condutor_de_outra_empresa_e_404(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        outra = await make_company(session, name="Vizinha")
        alheio = await make_driver(session, organization=outra)

        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.get(f"/api/organizacoes/{empresa.id}/frota/condutores/{alheio.id}")

        assert resposta.status_code == 404


class TestEdicaoENaoExclusao:
    async def test_desativar_e_um_patch(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        condutor = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.patch(
            f"/api/organizacoes/{empresa.id}/frota/condutores/{condutor.id}",
            json={"status": "inactive"},
        )

        assert resposta.status_code == 200
        assert resposta.json()["status"] == "inactive"

    async def test_nao_existe_delete_de_condutor(
        self,
        como: Como,
        session: AsyncSession,
        empresa: OrganizationModel,
    ) -> None:
        condutor = await make_driver(session, organization=empresa)
        gestor = await como(role=Role.MANAGER, org=empresa)

        resposta = await gestor.delete(
            f"/api/organizacoes/{empresa.id}/frota/condutores/{condutor.id}"
        )

        assert resposta.status_code == 405
