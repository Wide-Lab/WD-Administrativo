from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PageParams:
    """Parâmetros de paginação de uma consulta."""

    page: int = 1
    page_size: int = 20


@dataclass(frozen=True, slots=True)
class Page[T]:
    """Uma página de resultados."""

    items: list[T]
    total: int
    page: int
    page_size: int
