# GitHub Configuration

This directory contains templates and workflow definitions for AutoIntel’s CI/CD and community interactions.

- **workflows/**: GitHub Actions pipelines for CI (lint, test, security) and CD (build, push, deploy).
- **ISSUE_TEMPLATE/**: Standard bug report and feature request forms.
- **PULL_REQUEST_TEMPLATE.md**: Checklist for contributors.
- **CODEOWNERS**: Defines code review responsibilities.

## CI Pipeline

On every push and pull request to `main` or `develop`:
1. Install dependencies
2. Run ruff, black, isort (Python), ESLint, Prettier (Frontend)
3. Execute unit & integration tests with coverage
4. Build Docker images and run smoke tests

## CD Pipeline

On merge to `main`:
1. Build production Docker images
2. Push to GitHub Container Registry
3. Deploy to staging environment (automated) and production (manual approval)

Workflow files are located in `.github/workflows/`.
```