"""O motor de produção: um multimodal da OpenAI lendo o painel.

**Toda falha vira abstenção, e nenhuma vira 5xx.** Timeout, chave errada, cota estourada, JSON
malformado — em todos os casos a resposta é `value=None`, `confidence=LOW`, e a rota segue
respondendo 201 com a foto guardada. É a regra da spec: *um erro do fornecedor não pode bloquear
o lançamento da viagem — o produto é o registro, a leitura é conveniência.* Um 504 aqui
transformaria a indisponibilidade de terceiro na indisponibilidade do módulo.

O `note` de cada falha entra no log e **nunca** na resposta HTTP."""

import asyncio
import base64
import json
import logging

from src.modules.frota.application.ports.odometer_reader import OdometerReadingResult
from src.modules.frota.domain.entities import ReadingConfidence

logger = logging.getLogger(__name__)

_PROMPT = """Você está lendo a foto do painel de um veículo.

Devolva SOMENTE um objeto JSON, sem cercas de código, com exatamente estas chaves:
{"value": <int ou null>, "confidence": "high" | "medium" | "low", "note": "<texto curto>"}

- "value" é o hodômetro TOTAL do veículo, em quilômetros inteiros, sem separador de milhar.
- O painel costuma mostrar vários números: velocímetro, relógio, temperatura, tensão, autonomia,
  consumo e o hodômetro PARCIAL (trip/A/B). Nenhum deles é a resposta. O total é o de maior
  número de dígitos, normalmente 5 ou 6, e não vem acompanhado de "trip", "A", "B" nem de casa
  decimal.
- Se o total estiver ilegível, cortado, ou se você estiver em dúvida sobre qual número é o
  hodômetro, devolva "value": null. Uma abstenção é uma resposta correta; um palpite confiante e
  errado é o pior resultado possível, porque ninguém o confere.
- "confidence" descreve o quanto você confia no número: "high" só quando os dígitos estão nítidos
  e não há ambiguidade sobre qual mostrador é o total.
- "note" descreve em uma frase o que você viu, para o nosso log."""

_CONFIDENCES = {
    "high": ReadingConfidence.HIGH,
    "medium": ReadingConfidence.MEDIUM,
    "low": ReadingConfidence.LOW,
}


class OpenAIOdometerReader:
    def __init__(self, *, api_key: str, model: str, timeout_seconds: float) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._timeout = timeout_seconds

    @property
    def _engine(self) -> str:
        return f"openai:{self._model}"

    def _abstained(self, note: str) -> OdometerReadingResult:
        logger.warning("Leitura de hodômetro sem resultado (%s): %s", self._engine, note)
        return OdometerReadingResult(
            value=None,
            confidence=ReadingConfidence.LOW,
            engine=self._engine,
            note=note,
        )

    async def read(self, image: bytes, content_type: str) -> OdometerReadingResult:
        """Manda a foto e devolve o que o modelo leu.

        O timeout é da spec (15s por default): estourou, a leitura vira `value=None` e a resposta
        continua 201. `asyncio.wait_for` por fora do SDK, e não só o timeout do cliente HTTP,
        porque o teto que interessa é o da requisição inteira — quem está esperando é uma pessoa
        de pé ao lado do carro, com o formulário aberto."""

        payload = base64.b64encode(image).decode("ascii")

        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": _PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{content_type};base64,{payload}"},
                                },
                            ],
                        }
                    ],
                    response_format={"type": "json_object"},
                ),
                timeout=self._timeout,
            )
        except TimeoutError:
            return self._abstained(f"O motor não respondeu em {self._timeout:.0f}s.")
        except Exception as exc:  # noqa: BLE001 — ver o docstring do módulo
            return self._abstained(f"O motor falhou: {type(exc).__name__}: {exc}")

        content = (response.choices[0].message.content or "").strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return self._abstained(f"O motor devolveu algo que não é JSON: {content[:200]!r}")

        return self._as_reading(parsed)

    def _as_reading(self, parsed: object) -> OdometerReadingResult:
        """O JSON do modelo traduzido pro contrato — desconfiando de cada campo.

        Um modelo pode devolver `"45210"` em vez de `45210`, `"média"` em vez de `"medium"`, ou
        um número negativo. Nada disso pode virar exceção: o pior caso aceitável aqui é uma
        abstenção, e é nele que todo caminho estranho desemboca."""

        if not isinstance(parsed, dict):
            return self._abstained(f"O motor devolveu um JSON que não é objeto: {parsed!r}")

        note = str(parsed.get("note") or "")
        raw_value = parsed.get("value")

        if raw_value is None:
            return self._abstained(note or "O motor se absteve.")

        try:
            value = int(str(raw_value).strip().replace(".", "").replace(",", ""))
        except ValueError:
            return self._abstained(f"O motor devolveu um valor não numérico: {raw_value!r}")

        if value < 0:
            return self._abstained(f"O motor devolveu um valor negativo: {value}")

        confidence = _CONFIDENCES.get(str(parsed.get("confidence")).lower(), ReadingConfidence.LOW)

        return OdometerReadingResult(
            value=value,
            confidence=confidence,
            engine=self._engine,
            note=note,
        )
