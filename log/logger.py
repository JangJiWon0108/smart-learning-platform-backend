from __future__ import annotations

import logging

PREFIX = "[smart-learning]"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"smart_learning.{name}")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter(
            f"{PREFIX} %(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger

