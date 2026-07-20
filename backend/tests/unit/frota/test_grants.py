"""O `grants` do descritor da frota — a estreia do mecanismo da spec 09.

Regra pura sobre um registry em memória: roda sem Docker."""

from collections.abc import Iterator

import pytest

from src.core.modules import register_module, registered_modules
from src.modules.access.domain.entities import Role
from src.modules.access.domain.permissions import module_permissions_for, validate_module_grants
from src.modules.frota.domain.permissions import GRANTS, MODULE_KEY, FrotaPermissions
from src.modules.frota.module import FROTA


class TestDescritor:
    def test_a_chave_e_frota(self) -> None:
        assert FROTA.key == MODULE_KEY == "frota"

    def test_tem_router(self) -> None:
        """O que separa um módulo de verdade do placeholder que ele era até a spec 10."""

        assert FROTA.router is not None

    def test_nao_atende_parceiro(self) -> None:
        """Frota é módulo de Empresa. Como um Parceiro alcança um módulo segue em aberto desde a
        spec 05, e nasce com Refeições — não aqui."""

        assert "partner" not in FROTA.personas

    def test_toda_capability_e_namespaced(self) -> None:
        """A regra que `register_module` cobra na subida. Sem ela, um módulo poderia conceder
        `organizations.write` — escalada de privilégio."""

        assert all(p.startswith("frota.") for p in FROTA.permissions)

    def test_o_catalogo_sao_as_sete(self) -> None:
        assert FROTA.permissions == frozenset(
            {
                FrotaPermissions.VEHICLES_READ,
                FrotaPermissions.VEHICLES_WRITE,
                FrotaPermissions.DRIVERS_READ,
                FrotaPermissions.DRIVERS_WRITE,
                FrotaPermissions.USAGES_READ,
                FrotaPermissions.USAGES_WRITE,
                FrotaPermissions.USAGES_WRITE_OWN,
            }
        )

    def test_o_helper_monta_a_capability_com_prefixo(self) -> None:
        assert FROTA.permission("vehicles.write") == FrotaPermissions.VEHICLES_WRITE


class TestQuemRecebeOQue:
    def test_company_admin_recebe_todas(self) -> None:
        assert GRANTS["company_admin"] == FROTA.permissions

    def test_manager_recebe_todas(self) -> None:
        """É ele o gestor de frota — e é aqui que o papel finalmente ganha capability. A spec 04
        o deixou com `frozenset()` dizendo que o que ele faz são capabilities de módulo."""

        assert GRANTS["manager"] == FROTA.permissions

    def test_collaborator_recebe_so_ler_veiculo_e_lancar_o_proprio(self) -> None:
        assert GRANTS["collaborator"] == frozenset(
            {FrotaPermissions.VEHICLES_READ, FrotaPermissions.USAGES_WRITE_OWN}
        )

    def test_collaborator_nao_le_condutores(self) -> None:
        """Ele lança em nome de si mesmo; a lista de condutores da Empresa não é dele."""

        assert FrotaPermissions.DRIVERS_READ not in GRANTS["collaborator"]

    def test_collaborator_nao_apaga(self) -> None:
        """`DELETE` fica fora do `write_own` de propósito: quem apaga a própria viagem apaga a
        evidência. Corrigir, sim; sumir, é ato do gestor."""

        assert FrotaPermissions.USAGES_WRITE not in GRANTS["collaborator"]

    @pytest.mark.parametrize("papel", ["hr", "finance"])
    def test_hr_e_finance_nao_recebem_nada(self, papel: str) -> None:
        assert papel not in GRANTS

    def test_platform_admin_nao_recebe_nada(self) -> None:
        """A Widelab vende módulo; ela não opera a frota do cliente. `validate_module_grants`
        derrubaria a subida se esta linha existisse."""

        assert Role.PLATFORM_ADMIN.value not in GRANTS


class TestChegaAoPapel:
    """O mecanismo da spec 09 ligando o descritor ao mapa do kernel.

    **Registrar é ato de `mount_module`, não de `import`** — e é por isso que estes testes
    registram o descritor à mão. Importar `module.py` só define o `FROTA`; quem o põe no registry
    que `module_permissions_for` varre é o `mount_routes`. Sem esta fixture os testes abaixo
    passariam a testar um registry vazio, que é o pior tipo de verde."""

    @pytest.fixture(autouse=True)
    def _frota_registrada(self, registry_isolado: None) -> Iterator[None]:
        register_module(FROTA)
        yield

    def test_o_descritor_entrou_no_registry(self) -> None:
        assert any(d.key == "frota" for d in registered_modules())

    def test_manager_ganha_as_capabilities_de_frota(self) -> None:
        """O papel que sai de `PERMISSIONS_BY_ROLE` com `frozenset()` vazio — então o que aparecer
        aqui **só** pode ter vindo do descritor."""

        assert module_permissions_for(Role.MANAGER) >= FROTA.permissions

    def test_collaborator_ganha_so_as_duas(self) -> None:
        granted = module_permissions_for(Role.COLLABORATOR)

        assert FrotaPermissions.VEHICLES_READ in granted
        assert FrotaPermissions.USAGES_WRITE_OWN in granted
        assert FrotaPermissions.VEHICLES_WRITE not in granted

    def test_hr_nao_ganha_nada_de_frota(self) -> None:
        assert not any(p.startswith("frota.") for p in module_permissions_for(Role.HR))

    def test_platform_admin_nao_ganha_nada_de_frota(self) -> None:
        assert not any(p.startswith("frota.") for p in module_permissions_for(Role.PLATFORM_ADMIN))

    def test_validate_module_grants_aceita_o_descritor_real(self) -> None:
        """A app sobe: nenhum papel inexistente, nenhuma concessão à Plataforma."""

        validate_module_grants()


class TestSubidaRecusaOErrado:
    """As duas falhas de subida, cobradas no descritor **real** da frota."""

    @pytest.fixture(autouse=True)
    def _isolado(self, registry_isolado: None) -> Iterator[None]:
        """`_modules` é global de processo — sem isolar, um descritor inválido vazaria pros
        testes seguintes. Ver o docstring da fixture."""

        yield

    def test_capability_fora_do_namespace_nao_sobe(self) -> None:
        from dataclasses import replace

        invasor = replace(FROTA, grants={"manager": frozenset({"organizations.write"})})

        with pytest.raises(RuntimeError, match="fora do próprio namespace"):
            register_module(invasor)

    def test_papel_inexistente_nao_sobe(self) -> None:
        from dataclasses import replace

        com_typo = replace(
            FROTA,
            key="frota_typo",
            grants={"colaborador": frozenset({"frota_typo.vehicles.read"})},
        )
        register_module(com_typo)

        with pytest.raises(RuntimeError, match="papéis que não existem"):
            validate_module_grants()

    def test_conceder_a_plataforma_nao_sobe(self) -> None:
        from dataclasses import replace

        generoso = replace(
            FROTA,
            key="frota_generosa",
            grants={"platform_admin": frozenset({"frota_generosa.vehicles.read"})},
        )
        register_module(generoso)

        with pytest.raises(RuntimeError, match="não concede à Plataforma"):
            validate_module_grants()
