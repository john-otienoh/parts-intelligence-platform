-- ============================================================
-- BE FORWARD Parts Intelligence — PostgreSQL Schema
-- Bronze → Silver → Gold architecture
-- ============================================================

CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- ------------------------------------------------------------
-- BRONZE: immutable raw landing area
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bronze.listings_raw (
    source_key   TEXT PRIMARY KEY,
    ref_no       TEXT,
    url          TEXT NOT NULL,
    scraped_at   TIMESTAMPTZ NOT NULL,
    raw_json     JSONB NOT NULL,
    ingested_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bronze_ref_no ON bronze.listings_raw(ref_no);
CREATE INDEX IF NOT EXISTS idx_bronze_scraped_at ON bronze.listings_raw(scraped_at);

-- ------------------------------------------------------------
-- SILVER: normalised, typed entities
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS silver.parts (
    id              SERIAL PRIMARY KEY,
    ref_no          TEXT NOT NULL,
    scraped_at      TIMESTAMPTZ NOT NULL,
    url             TEXT,
    title           TEXT,
    condition       TEXT,
    make            TEXT,
    model           TEXT,
    product_name    TEXT,
    model_code      TEXT,
    reg_year_month  TEXT,
    mileage         TEXT,
    engine_model    TEXT,
    engine_size     TEXT,
    fuel            TEXT,
    drive           TEXT,
    transmission    TEXT,
    genuine_parts_no TEXT,
    description     TEXT,
    people_viewing  INTEGER,
    UNIQUE (ref_no, scraped_at)
);

CREATE TABLE IF NOT EXISTS silver.prices (
    id               SERIAL PRIMARY KEY,
    ref_no           TEXT NOT NULL,
    scraped_at       TIMESTAMPTZ NOT NULL,
    currency         TEXT,
    original_price   NUMERIC(12,2),
    current_price    NUMERIC(12,2),
    you_save_amount  NUMERIC(12,2),
    you_save_percent INTEGER,
    is_bargain       BOOLEAN,
    UNIQUE (ref_no, scraped_at)
);

CREATE TABLE IF NOT EXISTS silver.shipping_options (
    id                  SERIAL PRIMARY KEY,
    ref_no              TEXT NOT NULL,
    scraped_at          TIMESTAMPTZ NOT NULL,
    destination_port    TEXT,
    freight_method      TEXT,
    price               NUMERIC(12,2),
    currency            TEXT,
    etd                 TEXT,
    eta                 TEXT,
    estimated_delivery  TEXT
);

CREATE TABLE IF NOT EXISTS silver.similar_items (
    id            SERIAL PRIMARY KEY,
    listing_ref_no TEXT NOT NULL,
    scraped_at     TIMESTAMPTZ NOT NULL,
    similar_ref_no TEXT,
    name           TEXT,
    url            TEXT,
    image          TEXT,
    condition      TEXT,
    price          NUMERIC(12,2),
    original_price NUMERIC(12,2),
    currency       TEXT,
    discount_label TEXT,
    tag            TEXT
);

CREATE TABLE IF NOT EXISTS silver.images (
    id         SERIAL PRIMARY KEY,
    ref_no     TEXT NOT NULL,
    scraped_at TIMESTAMPTZ NOT NULL,
    image_url  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS silver.reviews (
    id                SERIAL PRIMARY KEY,
    ref_no            TEXT NOT NULL,
    scraped_at        TIMESTAMPTZ NOT NULL,
    review_id         TEXT,
    rating            INTEGER,
    reviewer_name     TEXT,
    reviewer_country  TEXT,
    date              TEXT,
    verified_buyer    BOOLEAN,
    review_text       TEXT
);

-- ------------------------------------------------------------
-- GOLD: materialised reporting views
-- ------------------------------------------------------------
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.daily_price_summary AS
SELECT
    ref_no,
    DATE(scraped_at) AS scrape_date,
    current_price,
    original_price,
    you_save_percent,
    is_bargain,
    scraped_at
FROM silver.prices
ORDER BY scrape_date DESC, ref_no;

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.shipping_cost_by_port AS
SELECT
    destination_port,
    freight_method,
    COUNT(*)        AS option_count,
    AVG(price)      AS avg_price,
    MIN(price)      AS min_price,
    MAX(price)      AS max_price
FROM silver.shipping_options
GROUP BY destination_port, freight_method;

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.parts_summary AS
SELECT
    silver.parts.ref_no,              -- qualified to remove ambiguity
    silver.parts.title,
    silver.parts.make,
    silver.parts.model,
    silver.parts.product_name,
    silver.parts.model_code,
    silver.parts.reg_year_month,
    silver.parts.mileage,
    silver.parts.engine_model,
    silver.parts.engine_size,
    silver.parts.fuel,
    silver.parts.drive,
    silver.parts.transmission,
    silver.parts.genuine_parts_no,
    COUNT(DISTINCT silver.images.id) AS image_count,
    COUNT(DISTINCT silver.reviews.id) AS review_count,
    AVG(silver.reviews.rating) AS avg_rating
FROM silver.parts
LEFT JOIN silver.images ON silver.parts.ref_no = silver.images.ref_no
LEFT JOIN silver.reviews ON silver.parts.ref_no = silver.reviews.ref_no
GROUP BY
    silver.parts.ref_no,
    silver.parts.title,
    silver.parts.make,
    silver.parts.model,
    silver.parts.product_name,
    silver.parts.model_code,
    silver.parts.reg_year_month,
    silver.parts.mileage,
    silver.parts.engine_model,
    silver.parts.engine_size,
    silver.parts.fuel,
    silver.parts.drive,
    silver.parts.transmission,
    silver.parts.genuine_parts_no;
    
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.shipping_summary AS
SELECT
    ref_no,
    COUNT(DISTINCT destination_port) AS port_count,
    COUNT(DISTINCT freight_method) AS method_count,
    AVG(price) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM silver.shipping_options
GROUP BY ref_no;