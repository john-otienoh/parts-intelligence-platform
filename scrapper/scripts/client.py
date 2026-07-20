"""Reusable HTTP client with polite retries and realistic headers."""

from __future__ import annotations

import random
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import Config


class ScraperClient:
    """Session wrapper with automatic retries, backoff, and polite delays."""

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": cfg.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        retry = Retry(
            total=cfg.retries,
            backoff_factor=0.5,
            status_forcelist=list(self.RETRYABLE_STATUS_CODES),
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    def get(self, url: str, **kwargs) -> requests.Response:
        """GET with configured timeout and polite random delay afterwards."""
        response = self._session.get(url, timeout=self._cfg.request_timeout, **kwargs)
        response.raise_for_status()
        time.sleep(random.uniform(*self._cfg.delay_range))
        return response

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "ScraperClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()
