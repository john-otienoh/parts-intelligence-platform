# Sample Datasets

Placeholder directory for sample automotive marketplace data used during development, testing, and demonstrations.

## Contents

- `sample_listings.json` – A curated set of 50 listing records in the scraper’s raw JSON format.
- `bronze_sample.csv` – Pre‑validated data for loading directly into the Bronze layer.
- `shipping_rates.csv` – Reference shipping cost lookup table.

## Usage

To load sample data for a quick start:
```bash
python scripts/seed_database.py --dataset datasets/bronze_sample.csv
```

Note: Do not commit real production data. All sample files should be anonymized and small in size.
```