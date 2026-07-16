# Data Collection Layer

## Overview

The Scraper module is responsible for acquiring raw automotive marketplace data. It is designed as a resilient, scalable ingestion service that collects product listings, prices, shipping information, and images while handling incremental updates, duplicates, and failures gracefully.

## Supported Marketplaces

| Marketplace | Status    |
| ----------- | --------- |
| BeForward   | Supported |
| eBay Motors | Planned   |
| Yahoo Auctions JP | Planned |
| Croooober   | Planned |

## Architecture

```text
Scheduler → Scraping Controller
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
 Product Spider  Shipping Spider  Image Spider
    │           │           │
    └───────────┼───────────┘
                ▼
        Data Normalization
                ▼
         Raw JSON Storage
                ▼
           Bronze Layer
```

## Workflow

1. Load configuration (marketplace URLs, selectors, delays).
2. Fetch listing pages and extract product URLs.
3. Visit each listing, extract metadata, shipping info, and download images.
4. Normalize output into a structured JSON schema.
5. Validate data quality and save immutable raw files.
6. Log session statistics.

## Output Structure

Each listing is stored as a JSON file:

```json
{
  "product": { "title": "...", "manufacturer": "...", ... },
  "price": { "current": "...", "currency": "...", ... },
  "shipping": { "cost": "...", "method": "...", ... },
  "images": [ "url1", "url2" ],
  "metadata": { "marketplace": "BeForward", "collected_at": "..." }
}
```

## Incremental & Duplicate Handling

- Tracked changes: price, shipping, availability.
- Duplicate detection via marketplace reference number, URL, or business key.
- Exponential backoff retry with configurable limits.

## Running a Scrape

```bash
python scraper/run.py --marketplace beforward
```

Logs and raw data are written to `scraper/data/`.

## Configuration

Scraper settings (timeouts, concurrency, user agent) are in `scraper/config.py`. Respect the target website’s robots.txt and add appropriate delays.

## Adding a New Marketplace

Implement a new Spider class inheriting from `BaseSpider` and register it in the controller. See `spiders/_template.py` for guidance.