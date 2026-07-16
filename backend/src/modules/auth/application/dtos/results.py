from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Par de tokens emitido após autenticação ou renovação."""

    access_token: str
