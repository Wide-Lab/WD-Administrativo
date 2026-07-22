"""A leitura de hodômetro por foto, contra Postgres de verdade.

Critérios 2 a 6, 8, 9, 10 e 12 da spec 11. **Nenhum teste aqui fala com a rede**: o motor é o
`StubOdometerReader` e o storage é um diretório do `tmp_path`, os dois injetados pelas portas —
que é exatamente o que elas existem pra permitir.

O critério 11 (acerto do motor sobre fotos reais) **não** mora aqui de propósito: ele exige o
adaptador de produção, chave de verdade e as fotos do spike, e a spec o coloca fora da suíte
automatizada."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.storage import LocalDirectoryStorage
from src.modules.access.adapters.db.models import Organization as OrganizationModel
from src.modules.access.domain.entities import Role
from src.modules.frota.domain.entities import ReadingConfidence, VehicleStatus
from tests.conftest import Como
from tests.factories import make_company, make_reading, make_user, make_vehicle
from tests.integration.frota.conftest import ComoCondutor, Motor, foto_jpeg

ULTIMO = 45_180
"""O `initial_odometer` dos veículos destes testes — o prior contra o qual o `plausivel` decide."""


def rota(org: OrganizationModel, vehicle_id: object) -> str:
    return f"/api/organizacoes/{org.id}/frota/veiculos/{vehicle_id}/hodometro/leituras"


def foto(
    content: bytes | None = None,
    content_type: str = "image/jpeg",
) -> dict[str, tuple[str, bytes, str]]:
    """O `files=` de um upload de foto, pronto pra `client.post`."""

    return {"foto": ("painel.jpg", content if content is not None else foto_jpeg(), content_type)}


class TestLeituraFeliz:
    """Critério 2: 201 com os cinco campos, linha gravada e objeto no storage sob a chave certa."""

    async def test_responde_201_com_o_numero_lido(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        motor(value=45_210)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["valor"] == 45_210
        assert corpo["confianca"] == "alta"
        assert corpo["plausivel"] is True
        assert corpo["ultimo_hodometro"] == ULTIMO
        assert corpo["delta"] == 30

    async def test_grava_a_linha_com_a_storage_key(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        linha = (
            await session.execute(
                sa.text("SELECT * FROM odometer_readings WHERE id = :id"),
                {"id": resposta.json()["id"]},
            )
        ).one()
        assert linha.storage_key
        assert linha.value_read == 45_210
        assert linha.engine == "stub:teste"

    async def test_a_chave_comeca_pelo_organization_id(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """Não é segurança (a autorização é das rotas), é operação: apagar um tenant ou auditar
        consumo vira prefixo, não `SELECT`."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        chave = (
            await session.execute(
                sa.text("SELECT storage_key FROM odometer_readings WHERE id = :id"),
                {"id": resposta.json()["id"]},
            )
        ).scalar_one()
        assert str(chave).startswith(f"{empresa.id}/frota/hodometro/")

    async def test_o_objeto_existe_no_storage(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        bytes_da_foto = foto_jpeg()

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(bytes_da_foto))

        chave = (
            await session.execute(
                sa.text("SELECT storage_key FROM odometer_readings WHERE id = :id"),
                {"id": resposta.json()["id"]},
            )
        ).scalar_one()
        assert await storage.get(str(chave)) == (bytes_da_foto, "image/jpeg")


class TestAbstencao:
    """Critério 3: o motor não conseguir ler **não é 4xx**. É resultado, e a evidência fica."""

    async def test_responde_201_com_valor_null(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        motor(value=None)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 201
        corpo = resposta.json()
        assert corpo["valor"] is None
        assert corpo["confianca"] == "baixa"
        assert corpo["plausivel"] is False
        assert corpo["delta"] is None
        assert corpo["ultimo_hodometro"] == ULTIMO

    async def test_a_linha_e_a_foto_sao_gravadas_assim_mesmo(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """A frase que a tela mostra depende disto: *"não consegui ler, mas a foto fica guardada
        do mesmo jeito"*. Se a linha não existisse, a frase seria mentira."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        motor(value=None)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        chave = (
            await session.execute(
                sa.text("SELECT storage_key FROM odometer_readings WHERE id = :id"),
                {"id": resposta.json()["id"]},
            )
        ).scalar_one()
        conteudo, _ = await storage.get(str(chave))
        assert conteudo


class TestFotoRecusada:
    """Critério 4: 413, 415 e 422 — e **nenhum dos três grava linha nem objeto**."""

    async def test_foto_de_9mb_responde_413(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await gestor.post(
            rota(empresa, veiculo.id),
            files=foto(b"\xff\xd8" + b"\x00" * (9 * 1024 * 1024)),
        )

        assert resposta.status_code == 413

    async def test_pdf_responde_415(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """Distinto do 422 de propósito: o formato foi entendido e recusado, e não é o conteúdo
        que está corrompido — a tela diz coisas diferentes nos dois casos."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await gestor.post(
            rota(empresa, veiculo.id),
            files={"foto": ("nota.pdf", b"%PDF-1.4 nada disso", "application/pdf")},
        )

        assert resposta.status_code == 415

    async def test_jpeg_corrompido_responde_422(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """O `content-type` é o que o cliente **afirma**, e afirmar é grátis. Quem confere é o
        decodificador."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await gestor.post(
            rota(empresa, veiculo.id),
            files=foto(b"isto nao e uma imagem, apesar do content-type"),
        )

        assert resposta.status_code == 422

    async def test_heic_responde_415(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """HEIC fica de fora e é decisão: o frontend reencoda pra JPEG antes de subir, então o
        formato nunca chega aqui — e aceitá-lo custaria `pillow-heif` no container por um caminho
        que ninguém percorre."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await gestor.post(
            rota(empresa, veiculo.id),
            files={"foto": ("painel.heic", foto_jpeg(), "image/heic")},
        )

        assert resposta.status_code == 415

    @pytest.mark.parametrize("caso", ["grande", "pdf", "corrompido"])
    async def test_nenhuma_recusa_grava_linha_nem_objeto(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
        tmp_path: Path,
        caso: str,
    ) -> None:
        """O payload é montado **dentro** do teste, e não no `parametrize`: 9 MB num parâmetro
        viram 9 MB de id de teste, e o pytest os imprime inteiros em qualquer relatório."""

        conteudos = {
            "grande": (b"\xff\xd8" + b"\x00" * (9 * 1024 * 1024), "image/jpeg"),
            "pdf": (b"%PDF-1.4", "application/pdf"),
            "corrompido": (b"nao sou imagem", "image/jpeg"),
        }
        conteudo, tipo = conteudos[caso]

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        await gestor.post(
            rota(empresa, veiculo.id),
            files={"foto": (f"{caso}.bin", conteudo, tipo)},
        )

        total = (
            await session.execute(sa.text("SELECT count(*) FROM odometer_readings"))
        ).scalar_one()
        assert total == 0
        assert not list(tmp_path.rglob("*.jpg"))


class TestAutorizacao:
    """Critério 5: `write_own` basta, `hr` não, e sem entitlement é 403 antes de tudo."""

    async def test_collaborator_com_write_own_consegue_ler(
        self,
        como_condutor: ComoCondutor,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
    ) -> None:
        """**Nenhuma capability nova**, e é decisão: ler hodômetro é parte de lançar viagem, e um
        `frota.odometer.read` separado poderia ser concedido a quem não pode lançar nada."""

        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await pessoa.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 201

    async def test_hr_recebe_403(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
    ) -> None:
        rh = await como(role=Role.HR, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        resposta = await rh.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 403

    async def test_sem_entitlement_e_403_antes_de_qualquer_validacao(
        self,
        como: Como,
        empresa_sem_frota: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
    ) -> None:
        """A foto vai **corrompida e enorme** de propósito: se a validação rodasse antes do
        guard, a resposta seria 413 ou 422 em vez de 403 — e o entitlement teria virado uma
        checagem que só acontece quando o resto passa."""

        gestor = await como(role=Role.MANAGER, org=empresa_sem_frota)
        veiculo = await make_vehicle(session, organization=empresa_sem_frota)

        resposta = await gestor.post(
            rota(empresa_sem_frota, veiculo.id),
            files=foto(b"lixo" * 3_000_000),
        )

        assert resposta.status_code == 403

    async def test_sem_sessao_e_401(
        self,
        client: AsyncClient,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
    ) -> None:
        veiculo = await make_vehicle(session, organization=empresa)

        resposta = await client.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 401


class TestVeiculoInvalido:
    """Critério 6."""

    async def test_veiculo_de_outra_empresa_e_404(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """404 e não 403: a resposta não pode virar oráculo de que o veículo existe em algum
        lugar. Mesma decisão do `GET /veiculos/{id}` da spec 10."""

        outra = await make_company(session, name="Empresa Alheia")
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo_alheio = await make_vehicle(session, organization=outra)

        resposta = await gestor.post(
            rota(empresa, veiculo_alheio.id),
            files=foto(foto_jpeg()),
        )

        assert resposta.status_code == 404

    async def test_veiculo_inexistente_e_404(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        import uuid

        gestor = await como(role=papel_gestor, org=empresa)

        resposta = await gestor.post(rota(empresa, uuid.uuid7()), files=foto(foto_jpeg()))

        assert resposta.status_code == 404

    async def test_veiculo_inactive_e_422(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """Veículo `inactive` não recebe uso novo (spec 10), então não há o que fotografar."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(
            session,
            organization=empresa,
            status=VehicleStatus.INACTIVE,
        )

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 422


class TestPlausivel:
    """Critério 8: as quatro bordas, e **nenhuma delas deixa de ser 201**."""

    @pytest.mark.parametrize(
        ("lido", "esperado"),
        [
            (ULTIMO, True),
            (ULTIMO + 2_000, True),
            (ULTIMO + 2_001, False),
            (ULTIMO - 1, False),
        ],
    )
    async def test_as_bordas(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
        lido: int,
        esperado: bool,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        motor(value=lido)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 201
        assert resposta.json()["plausivel"] is esperado

    async def test_implausivel_nao_vira_422(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """A spec 10 decidiu que divergência de hodômetro é **aviso, não bloqueio** — travar faria
        o usuário inventar um número, que é pior que o buraco. Existir uma foto não muda isso."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        motor(value=ULTIMO + 50_000)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 201
        assert resposta.json()["plausivel"] is False
        assert resposta.json()["valor"] == ULTIMO + 50_000


class TestLimiteDeLeituras:
    async def test_acima_de_30_por_hora_responde_429(
        self,
        como_condutor: ComoCondutor,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        tmp_path: Path,
    ) -> None:
        """Um dedo travado no botão custa dinheiro de fornecedor. As 30 anteriores entram por
        `INSERT` direto: o que se está afirmando é o teto, não a rota que o alimenta."""

        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)

        user_id = (
            await session.execute(
                sa.text("SELECT user_id FROM drivers WHERE organization_id = :org"),
                {"org": empresa.id},
            )
        ).scalar_one()

        for _ in range(30):
            await make_reading(
                session,
                organization=empresa,
                vehicle=veiculo,
                created_by=user_id,
            )

        resposta = await pessoa.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 429
        assert not list(tmp_path.rglob("*.jpg"))

    async def test_o_teto_e_por_usuario_e_nao_por_empresa(
        self,
        como_condutor: ComoCondutor,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
    ) -> None:
        """Um teto por tenant faria o segundo motorista do dia pagar pelo primeiro."""

        pessoa, _ = await como_condutor(role=Role.COLLABORATOR, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        outro = await make_user(session)

        for _ in range(30):
            await make_reading(
                session,
                organization=empresa,
                vehicle=veiculo,
                created_by=outro.id,
            )

        resposta = await pessoa.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.status_code == 201


class TestPurgaDeOrfas:
    """Critério 12: leitura velha que ninguém aponta some — linha **e** objeto."""

    async def test_orfa_de_25h_e_apagada_na_proxima_leitura(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        quem = await make_user(session)

        velha = await make_reading(
            session,
            organization=empresa,
            vehicle=veiculo,
            created_by=quem.id,
            created_at=datetime.now(UTC) - timedelta(hours=25),
        )
        await storage.put(velha.storage_key, b"foto-velha", "image/jpeg")

        await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        sobrou = (
            await session.execute(
                sa.text("SELECT count(*) FROM odometer_readings WHERE id = :id"),
                {"id": velha.id},
            )
        ).scalar_one()
        assert sobrou == 0

        from src.core.storage import ObjectNotFoundError

        with pytest.raises(ObjectNotFoundError):
            await storage.get(velha.storage_key)

    async def test_leitura_de_23h_nao_e_tocada(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        quem = await make_user(session)

        recente = await make_reading(
            session,
            organization=empresa,
            vehicle=veiculo,
            created_by=quem.id,
            created_at=datetime.now(UTC) - timedelta(hours=23),
        )

        await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        sobrou = (
            await session.execute(
                sa.text("SELECT count(*) FROM odometer_readings WHERE id = :id"),
                {"id": recente.id},
            )
        ).scalar_one()
        assert sobrou == 1

    async def test_leitura_velha_apontada_por_viagem_nao_e_tocada(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """Órfã é leitura que **ninguém aponta**. Uma foto de dois anos atrás anexada a uma viagem
        é a evidência que o módulo inteiro existe pra guardar."""

        from tests.factories import make_driver, make_usage

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        condutor = await make_driver(session, organization=empresa)
        quem = await make_user(session)

        antiga = await make_reading(
            session,
            organization=empresa,
            vehicle=veiculo,
            created_by=quem.id,
            created_at=datetime.now(UTC) - timedelta(days=400),
        )
        viagem = await make_usage(
            session,
            organization=empresa,
            vehicle=veiculo,
            driver=condutor,
            created_by=quem.id,
            started_at=datetime.now(UTC) - timedelta(days=400),
            ended_at=datetime.now(UTC) - timedelta(days=399),
            end_odometer=ULTIMO,
        )
        viagem.start_reading_id = antiga.id
        await session.commit()

        await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        sobrou = (
            await session.execute(
                sa.text("SELECT count(*) FROM odometer_readings WHERE id = :id"),
                {"id": antiga.id},
            )
        ).scalar_one()
        assert sobrou == 1

    async def test_orfa_de_outra_empresa_nao_e_tocada(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
    ) -> None:
        """A purga é tenant-scoped como todo o resto: a leitura de outra Empresa não é da conta
        desta requisição."""

        outra = await make_company(session, name="Empresa Vizinha")
        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        veiculo_alheio = await make_vehicle(session, organization=outra)
        quem = await make_user(session)

        alheia = await make_reading(
            session,
            organization=outra,
            vehicle=veiculo_alheio,
            created_by=quem.id,
            created_at=datetime.now(UTC) - timedelta(hours=48),
        )

        await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        sobrou = (
            await session.execute(
                sa.text("SELECT count(*) FROM odometer_readings WHERE id = :id"),
                {"id": alheia.id},
            )
        ).scalar_one()
        assert sobrou == 1


class TestConfianca:
    @pytest.mark.parametrize(
        ("enum", "rotulo"),
        [
            (ReadingConfidence.HIGH, "alta"),
            (ReadingConfidence.MEDIUM, "media"),
            (ReadingConfidence.LOW, "baixa"),
        ],
    )
    async def test_o_rotulo_sai_em_portugues(
        self,
        como: Como,
        empresa: OrganizationModel,
        session: AsyncSession,
        motor: Motor,
        storage: LocalDirectoryStorage,
        papel_gestor: Role,
        enum: ReadingConfidence,
        rotulo: str,
    ) -> None:
        """As colunas seguem em inglês (`high`/`medium`/`low`), como manda o `CLAUDE.md`; quem
        fala português é a borda HTTP."""

        gestor = await como(role=papel_gestor, org=empresa)
        veiculo = await make_vehicle(session, organization=empresa, initial_odometer=ULTIMO)
        motor(value=45_200, confidence=enum)

        resposta = await gestor.post(rota(empresa, veiculo.id), files=foto(foto_jpeg()))

        assert resposta.json()["confianca"] == rotulo
