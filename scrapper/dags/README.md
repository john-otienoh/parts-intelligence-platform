# Airflow DAGs — BE FORWARD Scraper

## DAGs

| DAG ID | Mode | Description |
|--------|------|-------------|
| `beforward_elt_pipeline` | **ELT** (recommended) | Raw JSON → Bronze → SQL transforms → Silver → Gold |
| `beforward_etl_pipeline` | **ETL** | Python transforms → direct Silver inserts → Gold |

Both run every **15 minutes** (`*/15 * * * *`) and are fully incremental.

---

## Setup

### 1. Install the Airflow Postgres provider

```bash
pip install apache-airflow-providers-postgres
```

### 2. Create the Airflow Postgres connection

In the Airflow UI (Admin → Connections) or via CLI:

```bash
airflow connections add postgres_default   --conn-type postgres   --conn-host localhost   --conn-port 5432   --conn-login postgres   --conn-password yourpassword   --conn-schema beforward
```

> The DAGs fall back to the `DATABASE_URL` environment variable if the connection is missing.

### 3. Ensure the project is on `PYTHONPATH`

Airflow must be able to import `config`, `database`, `scraper`, etc.

**Option A** — Set `PYTHONPATH` in your Airflow environment:

```bash
export PYTHONPATH="/path/to/beforward_scraper:${PYTHONPATH}"
```

**Option B** — Symlink the project into Airflow's `dags/` folder:

```bash
ln -s /path/to/beforward_scraper /opt/airflow/dags/beforward_scraper
```

**Option C** — Copy the DAGs and lib into your Airflow DAGs folder and adjust the `sys.path` insertion in each DAG (already done — the DAGs auto-detect their project root).

### 4. Initialise the database schema

Run once (outside Airflow or via a one-off `BashOperator`):

```bash
cd /path/to/beforward_scraper
python run_scheduled.py --init-schema
```

### 5. Enable the DAGs

```bash
airflow dags unpause beforward_elt_pipeline
airflow dags unpause beforward_etl_pipeline
```

---

## Task flow

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────────────┐     ┌─────────────────┐
│ discover_listings│────▶│ scrape_details  │────▶│ load/transform_silver   │────▶│ refresh_gold    │
│  (incremental)   │     │  (new URLs only)│     │  (ELT=SQL / ETL=Python) │     │  (materialized) │
└─────────────────┘     └─────────────────┘     └──────────────────────────┘     └─────────────────┘
```

---

## Metrics & observability

Each DAG pushes a `metrics` XCom at the end of the transform/load task.  
Example XCom value (ELT):

```json
{
  "bronze": 12,
  "silver_transformed": 87,
  "silver_parts": 12,
  "silver_prices": 12,
  "silver_shipping": 34,
  "silver_similar": 72,
  "silver_images": 45,
  "silver_reviews": 0,
  "gold_refreshed": 2,
  "mode": "elt"
}
```

You can surface these in a downstream reporting DAG or Grafana via the optional `bronze.pipeline_runs` audit table.

---

## Idempotency

* **Discover** queries `bronze.listings_raw` for known `ref_no`s and skips them.
* **Scrape** only hits URLs that passed the filter.
* **Bronze** insert uses `ON CONFLICT (source_key) DO NOTHING`.
* **Silver** tables have `(ref_no, scraped_at)` unique constraints.
* Re-running the same interval is safe — zero side-effects.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: config` | Add project root to `PYTHONPATH` |
| `Connection refused` | Verify `postgres_default` Airflow connection |
| `No new listings found` | Normal — means everything is already caught up |
| Task timeout (>12 min) | Increase `execution_timeout` in `DEFAULT_ARGS` or reduce `MAX_PAGES` |

---

## File layout

```
dags/
├── beforward_elt_dag.py      # ELT pipeline DAG
├── beforward_etl_dag.py      # ETL pipeline DAG
├── lib/
│   ├── __init__.py
│   ├── airflow_bridge.py     # Logger + DB URL adapter
│   └── metrics_reporter.py   # XCom + audit table helper
└── README.md
```