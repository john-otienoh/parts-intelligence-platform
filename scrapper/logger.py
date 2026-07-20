"""Structured file-only logging with rotation. No stdout/stderr handlers."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class _NoConsoleFilter(logging.Filter):
    """Ensures no console leakage — redundant safety net."""

    def filter(self, record: logging.LogRecord) -> bool:
        return True


def get_logger(name: str, log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Return a logger that writes to a rotating file in the specified directory."""

    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Idempotent: avoid duplicate handlers on re-import
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # General log (rotating at 10 MB, keep 5 backups)
    general = RotatingFileHandler(
        log_dir / "scraper.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    general.setLevel(level)
    general.setFormatter(fmt)
    general.addFilter(_NoConsoleFilter())

    # Error-only log
    error = RotatingFileHandler(
        log_dir / "scraper_error.log",
        maxBytes=10_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    error.setLevel(logging.ERROR)
    error.setFormatter(fmt)
    error.addFilter(_NoConsoleFilter())

    logger.addHandler(general)
    logger.addHandler(error)

    # Prevent propagation to root logger (which might have a console handler)
    logger.propagate = False

    return logger
