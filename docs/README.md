# AutoIntel Documentation Hub

Welcome to the AutoIntel documentation. Here you’ll find detailed guides, architecture decisions, and operational manuals.

## Table of Contents

- [Project Overview](../README.md)
- [Backend API](../backend/README.md)
- [Data Collection](../scraper/README.md)
- [Data Warehouse & ETL](../warehouse/README.md)
- [Analytics](../analytics/README.md)
- [Machine Learning](../ml/README.md)
- [Frontend](../frontend/README.md)
- [Infrastructure & Deployment](../infrastructure/README.md)
- [Contributing](../CONTRIBUTING.md)
- [Operations Manual](operations.md)
- [FAQ](faq.md)

## Architecture Diagrams

- [High‑Level Architecture](images/architecture_overview.png)
- [Data Flow](images/data_flow.png)
- [Database ERD](images/erd.png)

All images are stored in `docs/images/`.

## Building Documentation Locally

We use MkDocs Material:
```bash
pip install mkdocs-material
mkdocs serve
```
Open `http://localhost:8001` to view the full documentation site.