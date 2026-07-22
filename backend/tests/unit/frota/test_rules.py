"""As regras puras da frota — sem Docker, sem banco, sem FastAPI."""

import uuid
from datetime import UTC, datetime, timedelta

from src.modules.frota.domain.rules import (
    PLAUSIBLE_MAX_DELTA_KM,
    MileageGroupBy,
    UsageForReport,
    is_future,
    is_plausible,
    normalize_plate,
    odometer_delta,
    storage_key_for,
    summarize_mileage,
)

AGORA = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


class TestNormalizePlate:
    def test_sobe_para_maiusculas(self) -> None:
        assert normalize_plate("abc1d23") == "ABC1D23"

    def test_tira_espaco_das_pontas(self) -> None:
        assert normalize_plate("  ABC1D23  ") == "ABC1D23"

    def test_maiuscula_e_espaco_juntos(self) -> None:
        assert normalize_plate(" abc1d23 ") == "ABC1D23"

    def test_nao_mexe_no_hifen(self) -> None:
        """Unificar `ABC-1D23` e `ABC1D23` é palpite sobre formato de placa, e o custo do palpite
        errado é recusar uma placa legítima como duplicada. Ver o docstring da regra."""

        assert normalize_plate("abc-1d23") == "ABC-1D23"

    def test_e_idempotente(self) -> None:
        """Importa porque a normalização roda de novo em todo `PATCH` de placa."""

        uma_vez = normalize_plate(" abc1d23 ")
        assert normalize_plate(uma_vez) == uma_vez


class TestIsFuture:
    def test_futuro_e_futuro(self) -> None:
        assert is_future(AGORA + timedelta(seconds=1), AGORA) is True

    def test_passado_nao_e(self) -> None:
        """Retroativo é o caso normal da frota — o que se recusa é só o futuro."""

        assert is_future(AGORA - timedelta(days=3), AGORA) is False

    def test_o_proprio_agora_nao_e_futuro(self) -> None:
        """A borda que decide se lançar "agora" passa. Tem que passar."""

        assert is_future(AGORA, AGORA) is False


class TestSummarizeMileage:
    def test_soma_os_encerrados_por_veiculo(self) -> None:
        carro = uuid.uuid7()
        motorista = uuid.uuid7()

        resumo = summarize_mileage(
            usages=[
                UsageForReport(carro, motorista, start_odometer=1000, end_odometer=1150),
                UsageForReport(carro, motorista, start_odometer=1150, end_odometer=1200),
            ],
            group_by=MileageGroupBy.VEHICLE,
            labels={carro: "ABC1D23"},
        )

        assert len(resumo.groups) == 1
        grupo = resumo.groups[0]
        assert grupo.total_km == 200
        assert grupo.closed_usages == 2
        assert grupo.open_usages == 0
        assert grupo.label == "ABC1D23"

    def test_uso_aberto_conta_a_parte_e_nunca_como_zero(self) -> None:
        """A regra que impede o relatório de mentir pra baixo: "não sei" e "não rodou" não podem
        virar o mesmo número."""

        carro = uuid.uuid7()
        motorista = uuid.uuid7()

        resumo = summarize_mileage(
            usages=[
                UsageForReport(carro, motorista, start_odometer=1000, end_odometer=1150),
                UsageForReport(carro, motorista, start_odometer=1150, end_odometer=None),
            ],
            group_by=MileageGroupBy.VEHICLE,
            labels={carro: "ABC1D23"},
        )

        grupo = resumo.groups[0]
        assert grupo.total_km == 150
        assert grupo.closed_usages == 1
        assert grupo.open_usages == 1

    def test_veiculo_so_com_uso_aberto_aparece_com_zero_km_e_a_contagem(self) -> None:
        """Ele **aparece** — sumir do relatório esconderia que o carro está fora."""

        carro = uuid.uuid7()

        resumo = summarize_mileage(
            usages=[
                UsageForReport(carro, uuid.uuid7(), start_odometer=500, end_odometer=None),
            ],
            group_by=MileageGroupBy.VEHICLE,
            labels={carro: "XYZ9K88"},
        )

        grupo = resumo.groups[0]
        assert grupo.total_km == 0
        assert grupo.closed_usages == 0
        assert grupo.open_usages == 1

    def test_agrupa_por_condutor_quando_pedido(self) -> None:
        """O mesmo conjunto de usos, outro eixo: dois carros, um motorista só."""

        carro_a, carro_b = uuid.uuid7(), uuid.uuid7()
        motorista = uuid.uuid7()

        resumo = summarize_mileage(
            usages=[
                UsageForReport(carro_a, motorista, start_odometer=0, end_odometer=100),
                UsageForReport(carro_b, motorista, start_odometer=0, end_odometer=40),
            ],
            group_by=MileageGroupBy.DRIVER,
            labels={motorista: "Ana"},
        )

        assert len(resumo.groups) == 1
        assert resumo.groups[0].total_km == 140
        assert resumo.groups[0].label == "Ana"

    def test_separa_os_grupos(self) -> None:
        carro_a, carro_b = uuid.uuid7(), uuid.uuid7()

        resumo = summarize_mileage(
            usages=[
                UsageForReport(carro_a, uuid.uuid7(), start_odometer=0, end_odometer=100),
                UsageForReport(carro_b, uuid.uuid7(), start_odometer=0, end_odometer=40),
            ],
            group_by=MileageGroupBy.VEHICLE,
            labels={carro_a: "AAA1A11", carro_b: "BBB2B22"},
        )

        assert [(g.label, g.total_km) for g in resumo.groups] == [
            ("AAA1A11", 100),
            ("BBB2B22", 40),
        ]

    def test_ordena_por_rotulo(self) -> None:
        carro_a, carro_b = uuid.uuid7(), uuid.uuid7()

        resumo = summarize_mileage(
            usages=[
                UsageForReport(carro_a, uuid.uuid7(), start_odometer=0, end_odometer=10),
                UsageForReport(carro_b, uuid.uuid7(), start_odometer=0, end_odometer=10),
            ],
            group_by=MileageGroupBy.VEHICLE,
            labels={carro_a: "ZZZ9Z99", carro_b: "AAA1A11"},
        )

        assert [g.label for g in resumo.groups] == ["AAA1A11", "ZZZ9Z99"]

    def test_sem_uso_nenhum_e_uma_lista_vazia(self) -> None:
        resumo = summarize_mileage(
            usages=[],
            group_by=MileageGroupBy.VEHICLE,
            labels={},
        )

        assert resumo.groups == []

    def test_hodometro_com_lacuna_nao_e_erro(self) -> None:
        """Painel trocado e carro que rodou sem registro são reais demais pra travar o
        lançamento: a divergência aparece como lacuna, não vira exceção. A segunda viagem começa
        200 km à frente de onde a primeira terminou, e o relatório soma só o que foi rodado."""

        carro = uuid.uuid7()

        resumo = summarize_mileage(
            usages=[
                UsageForReport(carro, uuid.uuid7(), start_odometer=1000, end_odometer=1100),
                UsageForReport(carro, uuid.uuid7(), start_odometer=1300, end_odometer=1350),
            ],
            group_by=MileageGroupBy.VEHICLE,
            labels={carro: "ABC1D23"},
        )

        assert resumo.groups[0].total_km == 150


class TestIsPlausible:
    """As bordas do `plausivel`, que é o critério 8 — e o ponto dele é que **nenhuma** delas vira
    4xx. O sinal é pra tela; a spec 10 já decidiu que divergência de hodômetro é aviso."""

    ULTIMO = 45_180

    def test_igual_ao_ultimo_e_plausivel(self) -> None:
        """O carro que não rodou desde o último registro. Borda inclusiva de baixo."""

        assert is_plausible(self.ULTIMO, self.ULTIMO) is True

    def test_o_teto_de_2000_km_e_plausivel(self) -> None:
        """`+2000` é o teto, não o primeiro valor recusado — borda inclusiva de cima."""

        assert is_plausible(self.ULTIMO + PLAUSIBLE_MAX_DELTA_KM, self.ULTIMO) is True

    def test_um_quilometro_acima_do_teto_nao_e(self) -> None:
        assert is_plausible(self.ULTIMO + PLAUSIBLE_MAX_DELTA_KM + 1, self.ULTIMO) is False

    def test_abaixo_do_ultimo_nao_e(self) -> None:
        """Hodômetro que anda pra trás — o caso que o aviso existe pra mostrar."""

        assert is_plausible(self.ULTIMO - 1, self.ULTIMO) is False

    def test_o_meio_da_faixa_e_plausivel(self) -> None:
        assert is_plausible(self.ULTIMO + 30, self.ULTIMO) is True


class TestOdometerDelta:
    def test_o_delta_e_a_diferenca(self) -> None:
        assert odometer_delta(45_210, 45_180) == 30

    def test_sem_valor_lido_nao_ha_delta(self) -> None:
        """`None` e não `0`: o motor se absteve, e "não sei" não pode virar "não rodou"."""

        assert odometer_delta(None, 45_180) is None

    def test_delta_negativo_e_devolvido_como_e(self) -> None:
        """Não é clampado pra zero: um hodômetro que andou pra trás é exatamente o que a tela
        precisa mostrar."""

        assert odometer_delta(45_100, 45_180) == -80


class TestStorageKeyFor:
    """A chave **sempre começa pelo tenant** — não é segurança (a autorização é das rotas), é
    operação: apagar um tenant ou auditar consumo vira prefixo, não `SELECT`."""

    ORG = uuid.UUID("01890000-0000-7000-8000-000000000001")
    LEITURA = uuid.UUID("01890000-0000-7000-8000-0000000000ff")

    def test_comeca_pelo_organization_id(self) -> None:
        chave = storage_key_for(self.ORG, self.LEITURA, "image/jpeg")

        assert chave.startswith(f"{self.ORG}/")

    def test_o_caminho_inteiro(self) -> None:
        assert (
            storage_key_for(self.ORG, self.LEITURA, "image/jpeg")
            == f"{self.ORG}/frota/hodometro/{self.LEITURA}.jpg"
        )

    def test_a_extensao_segue_o_content_type(self) -> None:
        """A spec escreve `.jpg` no exemplo, mas PNG e WebP também entram — e um PNG guardado sob
        `.jpg` confundiria justamente quem abre o bucket, que é o uso operacional que a chave
        existe pra servir. Ver `Como ficou` da spec 11."""

        assert storage_key_for(self.ORG, self.LEITURA, "image/png").endswith(".png")
        assert storage_key_for(self.ORG, self.LEITURA, "image/webp").endswith(".webp")
