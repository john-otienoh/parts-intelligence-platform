#!/usr/bin/env python3
"""Scheduled runner — entry point for cron / systemd timers.

Usage (cron every 15 minutes):
    */15 * * * * cd /path/to/project && /usr/bin/python3 run_scheduled.py --mode elt >> /dev/null 2>&1

Or for ETL mode:
    */15 * * * * cd /path/to/project && /usr/bin/python3 run_scheduled.py --mode etl >> /dev/null 2>&1

All output goes to rotating log files in logs/; stdout/stderr are silent by design.
"""

from __future__ import annotations
import argparse
from sqlalchemy import text
import sys
from pathlib import Path
from datetime import datetime, timezone
from config import Config
from logger import get_logger
from database import PostgresStore
from scripts.client import ScraperClient

logger = get_logger("scheduler", Config.from_env().log_dir)


def _run_etl(cfg: Config, store: PostgresStore, client: ScraperClient) -> dict:
    from etl_pipeline import ETLPipeline

    return ETLPipeline(cfg, store, client).run()


def _run_elt(cfg: Config, store: PostgresStore, client: ScraperClient) -> dict:
    from elt_pipeline import ELTPipeline

    return ELTPipeline(cfg, store, client).run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BE FORWARD incremental scraper scheduler"
    )
    parser.add_argument(
        "--mode",
        choices=["etl", "elt"],
        default="elt",
        help="Pipeline mode: etl (transform in Python) or elt (transform in SQL)",
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Run schema.sql against the database before the pipeline",
    )
    args = parser.parse_args()

    cfg = Config.from_env()
    store = PostgresStore(cfg)

    if args.init_schema:
        logger.info("Initialising database schema...")
        schema_path = Path(__file__).with_suffix("").parent / "sql" / "schema.sql"
        if schema_path.exists():
            with schema_path.open("r", encoding="utf-8") as f:
                sql = f.read()
            # Execute each statement safely
            with store.session() as sess:
                for stmt in sql.split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        sess.execute(text(stmt))
            logger.info("Schema initialised.")
        else:
            logger.warning(f"Schema file not found: {schema_path}")

    started = datetime.now(timezone.utc)
    logger.info(f"Scheduled run started | mode={args.mode} | ts={started.isoformat()}")

    try:
        with ScraperClient(cfg) as client:
            if args.mode == "etl":
                metrics = _run_etl(cfg, store, client)
            else:
                metrics = _run_elt(cfg, store, client)
    except Exception as exc:
        logger.critical(f"Pipeline crashed: {exc}", exc_info=True)
        return 1

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    logger.info(
        f"Scheduled run complete | mode={args.mode} | elapsed={elapsed:.1f}s | metrics={metrics}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
