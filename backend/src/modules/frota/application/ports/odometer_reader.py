"""A porta de leitura de hodômetro.

Fica **no módulo**, e não no `core`: ler hodômetro é capability da frota, não infra transversal.
Se um dia Refeições quiser ler nota fiscal, o que se compartilha é o `ObjectStorage`, não isto.

**É esta porta que garante que a suíte não fala com rede** — e esse é o motivo principal de ela
existir. Os testes injetam o `StubOdometerReader`; produção injeta o adaptador do fornecedor.

A decisão do motor está na spec 11 (`A decisão do motor`), e o resumo é: o caminho sem IA foi
medido num bake-off e **nunca produziu o valor correto** em ~38 configurações do Tesseract. O que
faz o multimodal ganhar não é ler dígito melhor — é resolver o problema que o pipeline clássico
não resolve de jeito nenhum: *qual dos números do painel é o hodômetro*."""

from dataclasses import dataclass
from typing import Protocol

from src.modules.frota.domain.entities import ReadingConfidence

__all__ = ["OdometerReader", "OdometerReadingResult"]


@dataclass(frozen=True, slots=True)
class OdometerReadingResult:
    """O que o motor devolveu.

    A spec chama este dataclass de `OdometerReading`; aqui ele ganhou o sufixo porque
    `OdometerReading` já é a **entidade persistida** em `domain/entities.py`, e as duas coisas
    convivem em quase todo arquivo desta spec. A forma — os quatro campos e seus significados —
    é a do contrato."""

    value: int | None
    """`None` = o motor se absteve, e **isso é resposta, não falha**: "não consegui ler" é o
    comportamento certo diante de foto tremida. A rota responde 201 com `valor: null`, e a tela
    pede pra digitar."""

    confidence: ReadingConfidence
    engine: str
    """`"openai:gpt-4o"` — gravado em cada leitura porque o motor vai trocar."""

    note: str
    """O que o motor viu. Entra no log, **nunca na resposta HTTP**: é material de diagnóstico
    nosso, e devolvê-lo daria à tela um texto de fornecedor pra exibir sem querer."""


class OdometerReader(Protocol):
    async def read(self, image: bytes, content_type: str) -> OdometerReadingResult: ...
