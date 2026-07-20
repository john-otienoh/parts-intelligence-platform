"""Centralised, immutable configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional
from dotenv import load_dotenv

load_dotenv()  # Load .env file if present

@dataclass(frozen=True)
class Config:
    """A centralised, immutable configuration loaded from environment variables."""

    db_url: str
    log_dir: Path
    data_dir: Path
    max_pages: int
    delay_range: Tuple[float, float]
    request_timeout: int
    retries: int
    batch_size: int
    user_agent: str

    @classmethod
    def from_env(cls) -> Config:
        """Build configuration from environment variables with sensible defaults."""
        db_url=os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL is not set.\n"
                "  • Export it:  export DATABASE_URL='postgresql://...'\n"
                "  • Or create a .env file in the project root."
            )
        return cls(
            db_url=db_url,
            log_dir=Path(os.getenv("LOG_DIR", "logs")),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            max_pages=int(os.getenv("MAX_PAGES", "5")),
            delay_range=(0.8, 1.5),
            request_timeout=20,
            retries=3,
            batch_size=int(os.getenv("BATCH_SIZE", "100")),
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
        )
