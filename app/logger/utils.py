import logging
import sys

from uvicorn.logging import DefaultFormatter


def get_uvicorn_logger() -> logging.Logger:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(DefaultFormatter())

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger
