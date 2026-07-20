#!/usr/bin/env python3
"""ETL Pipeline — Transform in Python, load clean Silver tables directly.

Flow:
  1. Discover listing URLs (skip known ref_nos).
  2. Scrape detail pages.
  3. Validate with Pydantic models.
  4. Insert raw JSON into Bronze (audit / idempotency).
  5. Insert normalised rows into Silver tables.
  6. Refresh Gold materialised views.
  7. Emit change summary (rows inserted per table).
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

logger = get_logger("etl_pipeline", Config.from_env().log_dir)


class ETLPipeline:
    def __init__(self, cfg: Config, store: PostgresStore, client: ScraperClient):
        self.cfg = cfg
        self.store = store
        self.client = client

    def run(self) -> Dict[str, int]:
        started = datetime.now(timezone.utc)
        logger.info("=== ETL Pipeline started ===")

        # 1. Incremental filter
        known = self.store.known_ref_nos()
        logger.info(f"Database already contains {len(known)} ref_nos")

        urls = discover_listings(self.client, self.cfg, known_refs=known)
        if not urls:
            logger.info("No new listings found; nothing to do.")
            return {
                "bronze": 0,
                "silver_parts": 0,
                "silver_prices": 0,
                "silver_shipping": 0,
                "silver_similar": 0,
                "silver_images": 0,
                "silver_reviews": 0,
                "gold_refreshed": 0,
            }

        # 2. Scrape
        listings = scrape_details(self.client, urls, self.cfg)
        if not listings:
            logger.warning("Scraping yielded zero valid listings.")
            return {}

        # 3. Load
        metrics = self._load(listings)

        # 4. Refresh gold
        self._refresh_gold()
        metrics["gold_refreshed"] = 4            # updated to actual count

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        logger.info(
            f"=== ETL Pipeline finished in {elapsed:.1f}s | metrics={metrics} ==="
        )
        return metrics

    def _load(self, listings: List[PartListing]) -> Dict[str, int]:
        metrics = {
            "bronze": 0,
            "silver_parts": 0,
            "silver_prices": 0,
            "silver_shipping": 0,
            "silver_similar": 0,
            "silver_images": 0,
            "silver_reviews": 0,
        }

        with self.store.session() as sess:
            for listing in listings:
                # Bronze (idempotent)
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
                metrics["bronze"] += 1

                specs = listing.specifications or {}

                # Silver: parts
                sess.execute(
                    text(
                        """
                        INSERT INTO silver.parts
                        (ref_no, scraped_at, url, title, condition, make, model, product_name,
                         model_code, reg_year_month, mileage, engine_model, engine_size, fuel,
                         drive, transmission, genuine_parts_no, description, people_viewing)
                        VALUES (:ref, :ts, :url, :title, :cond, :make, :model, :prod,
                                :code, :reg, :mile, :eng_m, :eng_s, :fuel, :drive, :trans,
                                :genuine, :desc, :view)
                        ON CONFLICT (ref_no, scraped_at) DO NOTHING
                        """
                    ),
                    {
                        "ref": listing.ref_no,
                        "ts": listing.scraped_at,
                        "url": listing.url,
                        "title": specs.get("Product Name"),
                        "cond": None if specs.get("Condition") == "-" else specs.get("Condition"),
                        "make": None if specs.get("Make") == "-" else specs.get("Make"),
                        "model": None if specs.get("Model") == "-" else specs.get("Model"),
                        "prod": specs.get("Product Name"),
                        "code": None if specs.get("Model Code") == "-" else specs.get("Model Code"),
                        "reg": None if specs.get("Reg. Year/month") == "-" else specs.get("Reg. Year/month"),
                        "mile": None if specs.get("Mileage") == "-" else specs.get("Mileage"),
                        "eng_m": None if specs.get("Engine Model") == "-" else specs.get("Engine Model"),
                        "eng_s": None if specs.get("Engine Size") == "-" else specs.get("Engine Size"),
                        "fuel": None if specs.get("Fuel") == "-" else specs.get("Fuel"),
                        "drive": None if specs.get("Drive") == "-" else specs.get("Drive"),
                        "trans": None if specs.get("Mission Type") == "-" else specs.get("Mission Type"),
                        "genuine": None if specs.get("Genuine Parts No.") == "-" else specs.get("Genuine Parts No."),
                        "desc": listing.description,
                        "view": listing.people_viewing_now,
                    },
                )
                metrics["silver_parts"] += 1

                # Silver: prices
                p = listing.price
                sess.execute(
                    text(
                        """
                        INSERT INTO silver.prices
                        (ref_no, scraped_at, currency, original_price, current_price,
                         you_save_amount, you_save_percent, is_bargain)
                        VALUES (:ref, :ts, :cur, :orig, :curp, :save, :pct, :bargain)
                        ON CONFLICT (ref_no, scraped_at) DO NOTHING
                        """
                    ),
                    {
                        "ref": listing.ref_no,
                        "ts": listing.scraped_at,
                        "cur": p.currency,
                        "orig": p.original_price,
                        "curp": p.current_price,
                        "save": p.you_save_amount,
                        "pct": p.you_save_percent,
                        "bargain": p.is_bargain_price,
                    },
                )
                metrics["silver_prices"] += 1

                # Silver: shipping
                for opt in listing.shipping.options:
                    sess.execute(
                        text(
                            """
                            INSERT INTO silver.shipping_options
                            (ref_no, scraped_at, destination_port, freight_method, price,
                             currency, etd, eta, estimated_delivery)
                            VALUES (:ref, :ts, :port, :method, :price, :cur, :etd, :eta, :est)
                            """
                        ),
                        {
                            "ref": listing.ref_no,
                            "ts": listing.scraped_at,
                            "port": opt.destination_port,
                            "method": opt.freight_method,
                            "price": opt.price,
                            "cur": opt.currency,
                            "etd": opt.etd,
                            "eta": opt.eta,
                            "est": opt.estimated_delivery,
                        },
                    )
                    metrics["silver_shipping"] += 1

                # Silver: similar items
                for sim in listing.similar_items:
                    sess.execute(
                        text(
                            """
                            INSERT INTO silver.similar_items
                            (listing_ref_no, scraped_at, similar_ref_no, name, url, image,
                             condition, price, original_price, currency, discount_label, tag)
                            VALUES (:ref, :ts, :sref, :name, :url, :img, :cond, :price, :orig, :cur, :disc, :tag)
                            """
                        ),
                        {
                            "ref": listing.ref_no,
                            "ts": listing.scraped_at,
                            "sref": sim.ref_no,
                            "name": sim.name,
                            "url": sim.url,
                            "img": sim.image,
                            "cond": sim.condition,
                            "price": sim.price,
                            "orig": sim.original_price,
                            "cur": sim.currency,
                            "disc": sim.discount_label,
                            "tag": sim.tag,
                        },
                    )
                    metrics["silver_similar"] += 1

                # Silver: images
                for img_url in listing.images:
                    sess.execute(
                        text(
                            "INSERT INTO silver.images (ref_no, scraped_at, image_url) VALUES (:ref, :ts, :img)"
                        ),
                        {"ref": listing.ref_no, "ts": listing.scraped_at, "img": img_url},
                    )
                    metrics["silver_images"] += 1

                # Silver: reviews
                if listing.reviews:
                    for rev in listing.reviews.reviews:
                        sess.execute(
                            text(
                                """
                                INSERT INTO silver.reviews
                                (ref_no, scraped_at, review_id, rating, reviewer_name,
                                 reviewer_country, date, verified_buyer, review_text)
                                VALUES (:ref, :ts, :rid, :rating, :name, :country, :date, :verified, :text)
                                """
                            ),
                            {
                                "ref": listing.ref_no,
                                "ts": listing.scraped_at,
                                "rid": rev.review_id,
                                "rating": rev.rating,
                                "name": rev.reviewer_name,
                                "country": rev.reviewer_country,
                                "date": rev.date,
                                "verified": rev.verified_buyer,
                                "text": rev.text,
                            },
                        )
                        metrics["silver_reviews"] += 1

        return metrics

    def _refresh_gold(self) -> None:
        with self.store.session() as sess:
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.parts_summary"))
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.shipping_summary"))
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.daily_price_summary"))
            sess.execute(text("REFRESH MATERIALIZED VIEW gold.shipping_cost_by_port"))
        logger.info("Gold materialised views refreshed.")


def main() -> int:
    cfg = Config.from_env()
    store = PostgresStore(cfg)
    with ScraperClient(cfg) as client:
        pipeline = ETLPipeline(cfg, store, client)
        metrics = pipeline.run()
    logger.info(f"ETL_SUMMARY | metrics={metrics}")
    return 0


if __name__ == "__main__":
    sys.exit(main())