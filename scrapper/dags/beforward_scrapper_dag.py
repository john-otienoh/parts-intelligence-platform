"""BE FORWARD Parts Intelligence — Airflow DAG

Runs every 15 minutes to incrementally scrape new auto-parts listings,
land them in PostgreSQL Bronze, promote to Silver, and refresh Gold
materialised views.

Task flow:
  discover_listings  →  scrape_details  →  load_bronze  →  transform_silver  →  refresh_gold

Intermediate files (shared via mounted volume):
  /opt/airflow/data/listing_urls.json
  /opt/airflow/data/scraped_details.json

All tasks are idempotent — re-running will never duplicate rows.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

# Ensure the project source is on the path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration helpers

def _get_cfg():
    """Build Config lazily — safe for Airflow worker processes."""
    from config import Config
    return Config.from_env()


def _get_store(cfg):
    from database import PostgresStore
    return PostgresStore(cfg)


def _get_logger(cfg):
    from logger import get_logger
    return get_logger("airflow.beforward", cfg.log_dir)


DATA_DIR = Path("/opt/airflow/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
URLS_PATH = DATA_DIR / "listing_urls.json"
DETAILS_PATH = DATA_DIR / "scraped_details.json"

# Task callables

def task_discover_listings(**context) -> str:
    from scripts.client import ScraperClient
    from scripts.listing import discover_listings as _discover

    cfg = _get_cfg()
    logger = _get_logger(cfg)
    logger.info("Task: discover_listings started")

    store = _get_store(cfg)
    known = store.known_ref_nos()
    logger.info(f"Known ref_nos in DB: {len(known)}")

    with ScraperClient(cfg) as client:
        urls = _discover(client, cfg, known_refs=known)

    URLS_PATH.write_text(json.dumps(urls, indent=2), encoding="utf-8")
    logger.info(f"Discovered {len(urls)} new URLs → {URLS_PATH}")

    context["ti"].xcom_push(key="url_count", value=len(urls))
    return str(URLS_PATH)


def task_scrape_details(**context) -> str:
    from scripts.client import ScraperClient
    from scripts.detail import scrape_details as _scrape
    from models import PartListing

    cfg = _get_cfg()
    logger = _get_logger(cfg)
    logger.info("Task: scrape_details started")

    urls = json.loads(URLS_PATH.read_text(encoding="utf-8"))
    if not urls:
        logger.info("No URLs to scrape; skipping.")
        DETAILS_PATH.write_text("[]", encoding="utf-8")
        return str(DETAILS_PATH)

    with ScraperClient(cfg) as client:
        listings = _scrape(client, urls, cfg)

    records = [listing.model_dump(mode="json") for listing in listings]
    DETAILS_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Scraped {len(records)} listings → {DETAILS_PATH}")

    context["ti"].xcom_push(key="listing_count", value=len(records))
    return str(DETAILS_PATH)


def task_load_bronze(**context) -> Dict[str, int]:
    from models import PartListing

    cfg = _get_cfg()
    logger = _get_logger(cfg)
    logger.info("Task: load_bronze started")

    records = json.loads(DETAILS_PATH.read_text(encoding="utf-8"))
    if not records:
        logger.info("No records to load; skipping.")
        return {"bronze_inserted": 0}

    store = _get_store(cfg)
    inserted = 0
    with store.session() as sess:
        for rec in records:
            listing = PartListing.model_validate(rec)
            sess.execute(
                """
                INSERT INTO bronze.listings_raw (source_key, ref_no, url, scraped_at, raw_json)
                VALUES (:sk, :ref, :url, :ts, :json)
                ON CONFLICT (source_key) DO NOTHING
                """,
                {
                    "sk": listing.source_key(),
                    "ref": listing.ref_no,
                    "url": listing.url,
                    "ts": listing.scraped_at,
                    "json": listing.to_raw_json(),
                },
            )
            inserted += 1

    logger.info(f"Bronze load complete: {inserted} rows inserted")
    context["ti"].xcom_push(key="bronze_inserted", value=inserted)
    return {"bronze_inserted": inserted}


def task_transform_silver(**context) -> Dict[str, int]:
    cfg = _get_cfg()
    logger = _get_logger(cfg)
    logger.info("Task: transform_silver started")

    store = _get_store(cfg)
    total = 0

    with store.session() as sess:
        r = sess.execute("""
            INSERT INTO silver.parts
            (ref_no, scraped_at, url, title, condition, make, model, product_name,
             model_code, reg_year_month, mileage, engine_model, engine_size, fuel,
             drive, transmission, genuine_parts_no, description, people_viewing)
            SELECT
                b.ref_no,
                b.scraped_at,
                b.url,
                b.raw_json->'specifications'->>'Product Name',
                NULLIF(b.raw_json->'specifications'->>'Condition', '-'),
                NULLIF(b.raw_json->'specifications'->>'Make', '-'),
                NULLIF(b.raw_json->'specifications'->>'Model', '-'),
                NULLIF(b.raw_json->'specifications'->>'Product Name', '-'),
                NULLIF(b.raw_json->'specifications'->>'Model Code', '-'),
                NULLIF(b.raw_json->'specifications'->>'Reg. Year/month', '-'),
                NULLIF(b.raw_json->'specifications'->>'Mileage', '-'),
                NULLIF(b.raw_json->'specifications'->>'Engine Model', '-'),
                NULLIF(b.raw_json->'specifications'->>'Engine Size', '-'),
                NULLIF(b.raw_json->'specifications'->>'Fuel', '-'),
                NULLIF(b.raw_json->'specifications'->>'Drive', '-'),
                NULLIF(b.raw_json->'specifications'->>'Mission Type', '-'),
                NULLIF(b.raw_json->'specifications'->>'Genuine Parts No.', '-'),
                b.raw_json->>'description',
                (b.raw_json->>'people_viewing_now')::int
            FROM bronze.listings_raw b
            LEFT JOIN silver.parts s USING (ref_no, scraped_at)
            WHERE s.ref_no IS NULL
            ON CONFLICT (ref_no, scraped_at) DO NOTHING
        """)
        parts_ins = r.rowcount

        r = sess.execute("""
            INSERT INTO silver.prices
            (ref_no, scraped_at, currency, original_price, current_price,
             you_save_amount, you_save_percent, is_bargain)
            SELECT
                b.ref_no,
                b.scraped_at,
                b.raw_json->'price'->>'currency',
                (b.raw_json->'price'->>'original_price')::numeric,
                (b.raw_json->'price'->>'current_price')::numeric,
                (b.raw_json->'price'->>'you_save_amount')::numeric,
                (b.raw_json->'price'->>'you_save_percent')::int,
                (b.raw_json->'price'->>'is_bargain_price')::boolean
            FROM bronze.listings_raw b
            LEFT JOIN silver.prices s USING (ref_no, scraped_at)
            WHERE s.ref_no IS NULL
            ON CONFLICT (ref_no, scraped_at) DO NOTHING
        """)
        prices_ins = r.rowcount

        r = sess.execute("""
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
        """)
        ship_ins = r.rowcount

        r = sess.execute("""
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
        """)
        sim_ins = r.rowcount

        r = sess.execute("""
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
        """)
        img_ins = r.rowcount

        r = sess.execute("""
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
        """)
        rev_ins = r.rowcount

    total = parts_ins + prices_ins + ship_ins + sim_ins + img_ins + rev_ins
    metrics = {
        "parts": parts_ins,
        "prices": prices_ins,
        "shipping": ship_ins,
        "similar": sim_ins,
        "images": img_ins,
        "reviews": rev_ins,
        "total_silver": total,
    }
    logger.info(f"Silver transform complete: {metrics}")
    context["ti"].xcom_push(key="silver_metrics", value=metrics)
    return metrics

# DAG definition

default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "start_date": datetime(2026, 7, 16),
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email_on_retry": False,
}

with DAG(
    dag_id="beforward_parts_intelligence",
    default_args=default_args,
    description="Incremental BE FORWARD scraper: Bronze → Silver → Gold",
    schedule_interval=timedelta(minutes=15),
    catchup=False,
    max_active_runs=1,
    tags=["scraping", "beforward", "parts", "elt"],
) as dag:

    discover = PythonOperator(
        task_id="discover_listings",
        python_callable=task_discover_listings,
    )

    scrape = PythonOperator(
        task_id="scrape_details",
        python_callable=task_scrape_details,
    )

    load_bronze = PythonOperator(
        task_id="load_bronze",
        python_callable=task_load_bronze,
    )

    transform_silver = PythonOperator(
        task_id="transform_silver",
        python_callable=task_transform_silver,
    )

    refresh_gold = PostgresOperator(
        task_id="refresh_gold_views",
        postgres_conn_id="postgres_default",
        sql="""
            REFRESH MATERIALIZED VIEW gold.daily_price_summary;
            REFRESH MATERIALIZED VIEW gold.shipping_cost_by_port;
        """,
    )

    discover >> scrape >> load_bronze >> transform_silver >> refresh_gold