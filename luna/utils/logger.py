"""
Logger da Luna com saída colorida via Rich.
"""

import logging
from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Configura e retorna o logger principal da Luna.

    Args:
        level: Nível de logging (default: INFO).

    Returns:
        Logger configurado com RichHandler.
    """
    logger = logging.getLogger("luna")
    logger.setLevel(level)

    # Evitar handlers duplicados se chamado mais de uma vez
    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger
