import logging


def configure_logging() -> None:
    """Configure the root logger for the application."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
