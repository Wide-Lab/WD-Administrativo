"""O motor que não fala com ninguém.

Serve a dois papéis, e os dois são deliberados:

1. **Os testes.** A suíte injeta este adaptador e é ele que garante que nenhum teste toca a rede.
2. **O dev sem chave.** Sem `OPENAI_API_KEY`, é este que responde — e ele **se abstém**, em vez de
   inventar um número. É o gêmeo do `LoggingEmailSender` da spec 06: o fluxo funciona fim a fim
   sem provedor configurado, e o que sai é honesto. Um stub que devolvesse `45210` em dev faria a
   tela parecer pronta e o primeiro teste em campo descobrir que nunca esteve."""

from src.modules.frota.application.ports.odometer_reader import OdometerReadingResult
from src.modules.frota.domain.entities import ReadingConfidence


class StubOdometerReader:
    def __init__(
        self,
        *,
        value: int | None = None,
        confidence: ReadingConfidence | None = None,
        engine: str = "stub",
        note: str = "Leitura simulada: nenhum motor de verdade foi consultado.",
    ) -> None:
        """
        Args:
            value (int | None):
                O que "ler". O default é `None` — abster-se —, que é o comportamento certo pra
                quem sobe o backend sem chave de fornecedor.
            confidence (ReadingConfidence | None):
                A confiança devolvida. Sem valor lido, é sempre `LOW`.
            engine (str):
                O que vai pra coluna `engine`.
            note (str):
                O que vai pro log.
        """

        self._value = value
        self._confidence = confidence or (
            ReadingConfidence.LOW if value is None else ReadingConfidence.HIGH
        )
        self._engine = engine
        self._note = note

    async def read(self, image: bytes, content_type: str) -> OdometerReadingResult:
        return OdometerReadingResult(
            value=self._value,
            confidence=self._confidence,
            engine=self._engine,
            note=self._note,
        )
