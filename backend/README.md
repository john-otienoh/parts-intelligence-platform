# Backend API

## Overview

The Backend API is the central communication layer of AutoIntel. It exposes secure, scalable, and well-documented REST endpoints that allow the frontend, dashboards, machine learning services, and external clients to interact with the platform.

## Architecture

```text
Client Applications
        │
        ▼
 API Gateway (future)
        │
        ▼
 FastAPI Server
   ┌────┼──────────┐
   │    │          │
Auth  Marketplace  Analytics  ML Services
   │    │          │
   └────┼──────────┘
        ▼
   PostgreSQL / Redis
```

## Key Components

### Modules
- **Authentication** – JWT‑based login, registration, token refresh, password reset.
- **Marketplace** – Search listings, product details, similar products.
- **Analytics** – KPIs, price trends, supplier stats, shipping metrics.
- **Machine Learning** – Price prediction, recommendations, anomaly detection.
- **Administration** – Trigger scrapers, ETL jobs, model retraining.

### Endpoint Design
- RESTful resource design with versioned prefixes (`/api/v1/`)
- Automatic OpenAPI documentation (Swagger UI & ReDoc)
- Pagination, filtering, and sorting on list endpoints
- Consistent JSON response envelopes

### Authentication & Authorization
- **JWT Access & Refresh Tokens**
- **Role‑Based Access Control** (Super Admin, Admin, Analyst, Viewer, etc.)
- Password hashing with salting
- Rate limiting and CORS configuration

### Background Processing
Long‑running tasks (scraping, ETL, model training) are offloaded to Celery workers backed by Redis.

## Running Locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/base.txt
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`

## Testing

```bash
pytest --cov=app tests/
```

Coverage target: 90%

## Configuration

Environment variables are defined in `.env` (see `.env.example`). Critical settings include database URL, Redis connection, JWT secret, and CORS origins.

## Additional Documentation

- [API Specification](http://localhost:8000/redoc)
- [Database Schema](../warehouse/README.md)
- [Search Service Architecture](search/README.md) (future)
```