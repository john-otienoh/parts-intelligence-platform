# Analytics Platform

## Overview

The Analytics module transforms curated warehouse data (Gold layer) into interactive dashboards, KPIs, and automated business reports. It empowers stakeholders to monitor marketplace conditions, identify pricing opportunities, and compare supplier performance.

## Architecture

```text
Gold Layer Tables
      ↓
Analytics Views & Materialized Views
      ↓
┌─────┼──────────┐
▼     ▼          ▼
Executive KPIs  Operational Reports  ML Feature Store
      ↓
BI Dashboards (Superset / Streamlit / Power BI)
```

## Key Performance Indicators

- **Marketplace**: Total listings, new/removed per day, average listing age.
- **Pricing**: Average/median price, discount distribution, price volatility.
- **Shipping**: Average cost by destination, delivery duration trends.
- **Inventory**: Top manufacturers, vehicle models, categories.

## Dashboards

Pre‑built dashboards are available in `analytics/dashboards/`:

- **Executive Dashboard** – KPI cards, marketplace summary, high‑level trends.
- **Price Intelligence** – Historical price charts, discount analysis.
- **Shipping Analysis** – Cost maps, port comparisons.
- **Product Explorer** – Drill‑down by manufacturer/model/condition.

Dashboards can be viewed via Apache Superset or Streamlit (see `analytics/streamlit_app.py`).

## Reports

Automated reports (daily/weekly/monthly) are generated as PDF/Excel/CSV and stored in `analytics/reports/`. Custom SQL queries for ad‑hoc analysis are in `analytics/sql/`.

## Refresh Strategy

- Marketplace activity: after each scrape
- Pricing & shipping metrics: hourly (via Airflow)
- Inventory metrics: daily

## Running Locally

Launch Superset with Docker Compose (included) or run the Streamlit dashboard:
```bash
streamlit run analytics/streamlit_app.py
```
