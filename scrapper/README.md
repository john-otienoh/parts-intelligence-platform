# BE FORWARD Parts Intelligence — Production Scraper

A maintainable, DRY, production-grade scraper for BE FORWARD auto-parts listings with:

* **PostgreSQL** bronze/silver/gold warehouse (no DuckDB lock-in)
* **Incremental loading** — only new listings are scraped and inserted
* **File-only logging** with rotation (no console spam)
* **ETL + ELT** pipelines for flexibility
* **Cron-ready** scheduler with idempotent runs

---

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/beforward"
export MAX_PAGES=2          # search-result pages to crawl per run
export LOG_DIR=logs
export DATA_DIR=data
```

### 3. Initialise schema

```bash
python run_scheduled.py --mode elt --init-schema
```

### 4. Run manually

```bash
# ELT mode (recommended — transform in SQL)
python run_scheduled.py --mode elt

# ETL mode (transform in Python before loading)
python run_scheduled.py --mode etl
```

### 5. Schedule with cron (every 15 minutes)

```bash
crontab -e
```

Add:

```cron
*/15 * * * * cd /path/to/beforward_scraper && /usr/bin/python3 run_scheduled.py --mode elt >> /dev/null 2>&1
```

> All output is written to `logs/scraper.log` and `logs/scraper_error.log`.  
> `>> /dev/null 2>&1` is safe because nothing important goes to stdout.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  BE FORWARD │────▶│  Scraper     │────▶│  PostgreSQL     │
│  Website    │     │  (Python)    │     │  Bronze (raw)   │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                  │
                    ┌─────────────────────────────┘
                    ▼
           ┌─────────────────┐
           │  Silver (typed) │
           │  parts, prices  │
           │  shipping, etc. │
           └─────────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  Gold (MVs)     │
           │  daily summary  │
           │  shipping stats │
           └─────────────────┘
```

### Bronze (`bronze.listings_raw`)
Immutable raw JSON landing area.  
Primary key = `SHA256(ref_no | url | scraped_at)` — guarantees idempotency even if a listing is re-scraped.

### Silver (`silver.*`)
Normalised, typed tables:
* `parts` — vehicle & part specifications
* `prices` — price snapshots over time
* `shipping_options` — freight quotes per port
* `similar_items` — cross-sell recommendations
* `images` — image URLs
* `reviews` — customer reviews

### Gold (`gold.*`)
Materialised views for reporting:
* `daily_price_summary` — latest price per listing per day
* `shipping_cost_by_port` — aggregate freight statistics

---

## Pipelines

| Aspect | ETL (`etl_pipeline.py`) | ELT (`elt_pipeline.py`) |
|--------|------------------------|------------------------|
| Transform location | Python (Pydantic) | PostgreSQL (SQL) |
| Bronze usage | Audit trail | Source of truth for replay |
| Maintainability | Logic in Python | Logic in SQL (version with schema) |
| Performance | More round-trips | Single bulk SQL per table |
| Recommended for | Complex Python transforms | Standard normalisation |

Both pipelines share the same scraper modules (`scraper/`) and produce identical Silver tables.

---

## Incremental Strategy

1. Query `bronze.listings_raw` for all known `ref_no`s.
2. Crawl search-result pages.
3. Skip any listing whose `ref_no` is already known.
4. Scrape details **only** for new listings.
5. Insert with `ON CONFLICT DO NOTHING` as a safety net.

This minimises load on BE FORWARD's servers and keeps runs fast.

---

## Logging

All logs go to rotating files:

* `logs/scraper.log` — INFO and above (max 10 MB × 5 backups)
* `logs/scraper_error.log` — ERROR and above (max 10 MB × 5 backups)

No console output.  
Grep for `ETL_SUMMARY` or `ELT_SUMMARY` to see per-run metrics.

---

## Project Layout

```
beforward_scraper/
├── config.py              # Environment-driven configuration
├── logger.py              # File-only rotating logger
├── database.py            # SQLAlchemy PostgreSQL store
├── models.py              # Pydantic data models
├── etl_pipeline.py        # Extract → Transform → Load
├── elt_pipeline.py        # Extract → Load → Transform
├── run_scheduled.py       # Cron entry point
├── requirements.txt
├── sql/
│   └── schema.sql         # Bronze / Silver / Gold DDL
├── scraper/
│   ├── client.py          # HTTP session with retries
│   ├── parser.py          # lxml parsing (pure functions)
│   ├── listing.py         # URL discovery
│   └── detail.py          # Detail-page scraping
└── logs/                  # Rotating log files (gitignored)
```

---

## Notes

* Be polite: randomised delays (0.8–1.5 s) and automatic retries on 429/5xx.
* `data/` is optional — the pipelines stream directly into PostgreSQL.
* To force a full re-scrape, truncate `bronze.listings_raw` (Silver tables use `ON CONFLICT DO NOTHING`, so they won't duplicate).

---

## Airflow Orchestration

Two production DAGs are provided in `dags/`:

* `beforward_elt_pipeline` — recommended; SQL transforms inside Postgres
* `beforward_etl_pipeline` — Python transforms before Silver load

See [`dags/README.md`](dags/README.md) for setup instructions.