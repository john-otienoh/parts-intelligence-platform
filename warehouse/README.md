# Data Warehouse & ETL

## Overview

The Warehouse module implements the Medallion Architecture (Bronze → Silver → Gold) on PostgreSQL, orchestrated by Apache Airflow. It transforms raw marketplace data into clean, business‑ready analytical datasets.

## Pipeline Stages

```text
Raw JSON (from Scraper)
    ↓
Validation & Quality Checks
    ↓
Bronze Layer (immutable snapshots)
    ↓
Silver Layer (cleaned, standardized)
    ↓
Gold Layer (star schema, KPIs, analytics)
```

### Bronze Layer
- Append‑only tables storing raw validated records.
- Minimal transformation; serves as the source of truth.

### Silver Layer
- Deduplication, normalization of currencies/dates/units, enrichment (discount calculations, vehicle generation).
- Trusted datasets for operational use.

### Gold Layer
- Dimensional model: fact tables (listings, price history, shipping) + dimensions (product, vehicle, marketplace, date).
- Optimized for BI dashboards and ML feature extraction.

## Orchestration

Airflow DAGs schedule and manage:
- Incremental scraping → validation → bronze loading
- Silver transformation and deduplication
- Gold aggregation and materialized view refresh

Example DAG: `warehouse/airflow/dags/etl_main.py`

## dbt Integration

Data transformations are defined using dbt models in `warehouse/dbt/`. Run:

```bash
dbt run --profiles-dir ./warehouse/dbt
```

## Data Quality

- Schema validation with Pydantic/Pandera
- Business rule checks (price > 0, year ≤ current, etc.)
- Quality scores (Completeness, Accuracy, Consistency)
- Rejected records stored in a quarantine schema

## Database Schema

PostgreSQL schemas: `bronze`, `silver`, `gold`, `analytics`, `ml`.

Indexed columns: `listing_id`, `reference_number`, `marketplace_id`, `product_id`, `date_id`. Partitioned fact tables by quarter.

## Usage

Apply migrations:
```bash
alembic upgrade head
```

Trigger a full ETL run:
```bash
python warehouse/pipeline.py --full
```

Monitor via Airflow UI at `http://localhost:8080`.