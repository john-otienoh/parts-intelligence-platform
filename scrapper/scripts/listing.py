"""Discover listing URLs from BE FORWARD search-result pages."""

from __future__ import annotations

from typing import List, Set
from lxml import html

from config import Config
from logger import get_logger
from scripts.client import ScraperClient

logger = get_logger(__name__, Config.from_env().log_dir)
SEARCH_URL = "https://autoparts.beforward.jp/search/"


def discover_listings(
    client: ScraperClient, cfg: Config, known_refs: Set[str] | None = None
) -> List[str]:
    """Crawl search pages and return URLs for listings not already in `known_refs`."""

    known_refs = known_refs or set()
    discovered_urls: List[str] = []
    stop_early = False
    for page in range(1, cfg.max_pages + 1):
        if stop_early:
            logger.info("All remaining listings are known; stopping pagination early.")
            break

        try:
            resp = client.get(SEARCH_URL, params={"page": page, "list_type": "list"})
        except Exception as exc:
            logger.error(f"Failed to fetch search page {page}: {exc}")
            break

        tree = html.fromstring(resp.text)
        rows = tree.cssselect("tr.list-link-position:not(.list-genuine)")
        if not rows:
            logger.info(f"No more listings after page {page - 1}; stopping.")
            break

        new_on_page = 0
        for row in rows:
            name_wrap = row.cssselect(".td-name")
            if not name_wrap:
                continue
            a_tags = name_wrap[0].cssselect("a")
            if not a_tags:
                continue
            href = a_tags[0].get("href")
            if not href:
                continue

            # Extract ref_no from URL for cheap duplicate detection
            ref_no = href.rstrip("/").split("/")[-1]
            if ref_no in known_refs:
                continue

            discovered_urls.append(href)
            new_on_page += 1

        logger.info(
            f"Page {page}: {len(rows)} rows, {new_on_page} new, {len(discovered_urls)} total queued"
        )
        if new_on_page == 0:
            stop_early = True

    return discovered_urls
