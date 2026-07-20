"""Scrape individual listing detail pages."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from lxml import html

from config import Config
from logger import get_logger
from models import PartListing
from scripts.client import ScraperClient
from scripts import parser

logger = get_logger(__name__, Config.from_env().log_dir)


def scrape_detail(client: ScraperClient, url: str, cfg: Config) -> PartListing | None:
    """Scrape a single listing detail page and return the parsed data."""
    try:
        resp = client.get(url)
    except Exception as exc:
        logger.error(f"Failed to fetch detail page {url}: {exc}")
        return None

    tree = html.fromstring(resp.text)

    ref_no = parser._text(
        tree.xpath('//input[@name="data[parts_list][1][ref_no]"]/@value')
    )

    return PartListing(
        url=url,
        scraped_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ref_no=ref_no,
        item_location=parser.parse_item_location(tree),
        price=parser.parse_price_block(tree),
        people_viewing_now=parser.parse_people_viewing(tree),
        specifications=parser.parse_specifications(tree),
        description=parser.parse_description(tree),
        images=parser.parse_images(tree, url),
        shipping=parser.parse_shipping(tree),
        similar_items=parser.parse_similar_items(tree, url),
        reviews=parser.parse_reviews(tree),
    )


def scrape_details(
    client: ScraperClient, urls: List[str], cfg: Config
) -> List[PartListing]:
    """Scrape a batch of URLs, logging progress and tolerating individual failures."""
    results: List[PartListing] = []
    for idx, url in enumerate(urls, start=1):
        logger.info(f"[{idx}/{len(urls)}] Scraping detail: {url}")
        try:
            listing = scrape_detail(client, url, cfg)
            if listing:
                results.append(listing)
        except Exception as exc:
            logger.error(f"Failed to scrape {url}: {exc}", exc_info=True)
    return results
