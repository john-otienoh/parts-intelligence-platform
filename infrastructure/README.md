# Infrastructure & DevOps

## Overview

The infrastructure module contains everything needed to deploy, monitor, and maintain AutoIntel in a production‑like environment using Docker, CI/CD pipelines, and observability tools.

## Directory Structure

- `docker/` – Dockerfiles and Compose files for all services
- `nginx/` – Reverse proxy configuration
- `monitoring/` – Prometheus config, Grafana dashboards, alerting rules
- `scripts/` – Deployment and maintenance shell scripts
- `terraform/` – (future) Infrastructure‑as‑Code for cloud resources

## Services (Docker Compose)

| Service      | Port  | Description                   |
| ------------ | ----- | ----------------------------- |
| backend      | 8000  | FastAPI server                |
| frontend     | 3000  | Next.js app                   |
| postgres     | 5432  | PostgreSQL database           |
| redis        | 6379  | Cache & message broker        |
| airflow      | 8080  | Workflow scheduler            |
| celery       | –     | Background task workers       |
| prometheus   | 9090  | Metrics collection            |
| grafana      | 3001  | Monitoring dashboards         |
| nginx        | 80    | Reverse proxy & static files  |

## CI/CD (GitHub Actions)

Pipelines in `.github/workflows/`:
- **CI**: Lint, test, security scan on every PR
- **CD**: Build Docker images, push to registry, deploy to staging/production upon merge to main

## Monitoring & Logging

- **Prometheus** scrapes metrics from backend, database, Redis, and scraper
- **Grafana** dashboards visualize infrastructure & business KPIs
- **Sentry** for error tracking
- **Loguru** structured logs aggregated via the ELK stack (optional)

## Deployment

### Local Development
```bash
docker compose up -d
```

### Production (example with AWS ECS)
1. Build images: `docker build -t autointel-api:latest .`
2. Push to ECR / Docker Hub
3. Update ECS task definition & service
4. Apply database migrations

Detailed deployment guide: [docs/deployment.md](../docs/deployment.md)

## Backup & Recovery

- PostgreSQL: `pg_dump` scheduled via cron, stored in S3 (or volume)
- Redis: AOF persistence enabled
- Configuration: backed up via Git and volume snapshots