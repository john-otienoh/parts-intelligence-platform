#!/usr/bin/env python3
"""ELT Pipeline — Load raw JSON first, then Transform inside PostgreSQL.

Flow:
  1. Discover listing URLs (skip known ref_nos).
  2. Scrape detail pages.
  3. Load raw JSON into Bronze (idempotent).
  4. Run SQL transformations to populate Silver tables.
  5. Refresh Gold materialised views.
  6. Emit change summary.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy import text
from config import Config
from database import PostgresStore
from logger import get_logger
from models import PartListing
from scripts.client import ScraperClient
from scripts.detail import scrape_details
from scripts.listing import discover_listings

logger = get_logger(__name__, Config.from_env().log_dir)


class ELTPipeline:
    """A simple ELT pipeline for scraping and loading BE FORWARD listings."""

    def __init__(self, cfg: Config, store: PostgresStore, client: ScraperClient):
        self.cfg = cfg
        self.store = store
        self.client = client

    def run(self) -> Dict[str, int]:
        """Run the ELT pipeline and return a summary of changes."""
        started = datetime.now(timezone.utc)
        logger.info("=== ELT Pipeline started ===")

        known = self.store.known_ref_nos()
        logger.info(f"Database already contains {len(known)} ref_nos")

        urls = discover_listings(self.client, self.cfg, known_refs=known)
        if not urls:
            logger.info("No new listings found; nothing to do.")
            return {"bronze": 0, "silver_transformed": 0, "gold_refreshed": 0}

        listings = scrape_details(self.client, urls, self.cfg)
        if not listings:
            logger.warning("Scraping yielded zero valid listings.")
            return {}

        bronze_count = self._load_bronze(listings)
        silver_count = self._transform_silver()
        self._refresh_gold()

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        metrics = {
            "bronze": bronze_count,
            "silver_transformed": silver_count,
            "gold_refreshed": 2,
        }
        logger.info(
            f"=== ELT Pipeline finished in {elapsed:.1f}s | metrics={metrics} ==="
        )
        return metrics

    def _load_bronze(self, listings: List[PartListing]) -> int:
        """Load scraped listings into the Bronze table, skipping duplicates."""
        count = 0
        with self.store.session() as sess:
            for listing in listings:
                sess.execute(
                    text(
                        """
                        INSERT INTO bronze.listings_raw (source_key, ref_no, url, scraped_at, raw_json)
                        VALUES (:sk, :ref, :url, :ts, :json)
                        ON CONFLICT (source_key) DO NOTHING
                        """
                    ),
                    {
                        "sk": listing.source_key(),
                        "ref": listing.ref_no,
                        "url": listing.url,
                        "ts": listing.scraped_at,
                        "json": listing.to_raw_json(),
                    },
                )
                count += 1
        logger.info(f"Loaded {count} rows into bronze.listings_raw")
        return count

    def _transform_silver(self) -> int:
        """Run SQL transformations to populate Silver tables."""
        with self.store.session() as sess:
            # Parts
            r = sess.execute(text("""
                INSERT INTO silver.parts
                (ref_no, scraped_at, url, title, condition, make, model, product_name,
                 model_code, reg_year_month, mileage, engine_model, engine_size, fuel,
                 drive, transmission, genuine_parts_no, description, people_viewing)
                SELECT
                    b.ref_no,
                    b.scraped_at,
                    b.url,
                    (b.raw_json::jsonb)->>'specifications'->>'Product Name',
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Condition', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Make', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Model', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Product Name', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Model Code', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Reg. Year/month', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Mileage', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Engine Model', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Engine Size', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Fuel', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Drive', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Mission Type', '-'),
                    NULLIF((b.raw_json::jsonb)->>'specifications'->>'Genuine Parts No.', '-'),
                    (b.raw_json::jsonb)->>'description',
                    ((b.raw_json::jsonb)->>'people_viewing_now')::int
                FROM bronze.listings_raw b
                LEFT JOIN silver.parts s USING (ref_no, scraped_at)
                WHERE s.ref_no IS NULL
                ON CONFLICT (ref_no, scraped_at) DO NOTHING
            """))
            parts_ins = r.rowcount

            # Prices
            r = sess.execute(text("""
                INSERT INTO silver.prices
                (ref_no, scraped_at, currency, original_price, current_price,
                 you_save_amount, you_save_percent, is_bargain)
                SELECT
                    b.ref_no,
                    b.scraped_at,
                    (b.raw_json::jsonb)->'price'->>'currency',
                    ((b.raw_json::jsonb)->'price'->>'original_price')::numeric,
                    ((b.raw_json::jsonb)->'price'->>'current_price')::numeric,
                    ((b.raw_json::jsonb)->'price'->>'you_save_amount')::numeric,
                    ((b.raw_json::jsonb)->'price'->>'you_save_percent')::int,
                    ((b.raw_json::jsonb)->'price'->>'is_bargain_price')::boolean
                FROM bronze.listings_raw b
                LEFT JOIN silver.prices s USING (ref_no, scraped_at)
                WHERE s.ref_no IS NULL
                ON CONFLICT (ref_no, scraped_at) DO NOTHING
            """))
            prices_ins = r.rowcount

            # Shipping
            r = sess.execute(text("""
                INSERT INTO silver.shipping_options
                (ref_no, scraped_at, destination_port, freight_method, price,
                 currency, etd, eta, estimated_delivery)
                SELECT
                    b.ref_no,
                    b.scraped_at,
                    opt->>'destination_port',
                    opt->>'freight_method',
                    (opt->>'price')::numeric,
                    opt->>'currency',
                    opt->>'etd',
                    opt->>'eta',
                    opt->>'estimated_delivery'
                FROM bronze.listings_raw b,
                LATERAL jsonb_array_elements((b.raw_json::jsonb)->'shipping'->'options') AS opt
                LEFT JOIN silver.shipping_options s
                  ON s.ref_no = b.ref_no AND s.scraped_at = b.scraped_at
                  AND s.destination_port = opt->>'destination_port'
                WHERE s.id IS NULL
            """))
            ship_ins = r.rowcount

            # Similar items
            r = sess.execute(text("""
                INSERT INTO silver.similar_items
                (listing_ref_no, scraped_at, similar_ref_no, name, url, image,
                 condition, price, original_price, currency, discount_label, tag)
                SELECT
                    b.ref_no,
                    b.scraped_at,
                    sim->>'ref_no',
                    sim->>'name',
                    sim->>'url',
                    sim->>'image',
                    sim->>'condition',
                    (sim->>'price')::numeric,
                    (sim->>'original_price')::numeric,
                    sim->>'currency',
                    sim->>'discount_label',
                    sim->>'tag'
                FROM bronze.listings_raw b,
                LATERAL jsonb_array_elements((b.raw_json::jsonb)->'similar_items') AS sim
                LEFT JOIN silver.similar_items s
                  ON s.listing_ref_no = b.ref_no AND s.scraped_at = b.scraped_at
                  AND s.similar_ref_no = sim->>'ref_no'
                WHERE s.id IS NULL
            """))
            sim_ins = r.rowcount

            # Images
            r = sess.execute(text("""
                INSERT INTO silver.images (ref_no, scraped_at, image_url)
                SELECT
                    b.ref_no,
                    b.scraped_at,
                    img
                FROM bronze.listings_raw b,
                LATERAL jsonb_array_elements_text((b.raw_json::jsonb)->'images') AS img
                LEFT JOIN silver.images s
                  ON s.ref_no = b.ref_no AND s.scraped_at = b.scraped_at AND s.image_url = img
                WHERE s.id IS NULL
            """))
            img_ins = r.rowcount

            # Reviews
            r = sess.execute(text("""
                INSERT INTO silver.reviews
                (ref_no, scraped_at, review_id, rating, reviewer_name,
                 reviewer_country, date, verified_buyer, review_text)
                SELECT
                    b.ref_no,
                    b.scraped_at,
                    rev->>'review_id',
                    (rev->>'rating')::int,
                    rev->>'reviewer_name',
                    rev->>'reviewer_country',
                    rev->>'date',
                    (rev->>'verified_buyer')::boolean,
                    rev->>'text'
                FROM bronze.listings_raw b,
                LATERAL jsonb_array_elements((b.raw_json::jsonb)->'reviews'->'reviews') AS rev
                LEFT JOIN silver.reviews s
                  ON s.ref_no = b.ref_no AND s.scraped_at = b.scraped_at
                  AND s.review_id = rev->>'review_id'
                WHERE s.id IS NULL
            """))
            rev_ins = r.rowcount

        total = parts_ins + prices_ins + ship_ins + sim_ins + img_ins + rev_ins
        logger.info(
            f"Silver transform complete: parts={parts_ins}, prices={prices_ins}, "
            f"shipping={ship_ins}, similar={sim_ins}, images={img_ins}, reviews={rev_ins}"
        )
        return total

    def _refresh_gold(self) -> None:
        """Refresh Gold materialised views."""
        with self.store.session() as sess:
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.parts_summary"))
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.shipping_summary"))
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.daily_price_summary"))
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.shipping_cost_by_port"))

        logger.info("Gold materialised views refreshed.")


def main():
    cfg = Config.from_env()
    store = PostgresStore(cfg)
    with ScraperClient(cfg) as client:
        pipeline = ELTPipeline(cfg, store, client)
        metrics = pipeline.run()
    logger.info(f"ELT_SUMMARY | metrics={metrics}")
    return 0


if __name__ == "__main__":
    sys.exit(main())