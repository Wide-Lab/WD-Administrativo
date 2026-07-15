import logging


def setup_logging(level: str = "INFO") -> None:
    """Configura o logging da aplicação.

    Args:
        level (str):
            Nível mínimo de log (ex.: "INFO", "DEBUG"). Vem de `Config.LOG_LEVEL`.
    """

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
