# Frontend Application

## Overview

A modern Single Page Application (SPA) built with React/Next.js that provides an intuitive interface to the AutoIntel platform. Users can browse listings, explore analytics dashboards, search for parts, and manage their accounts.

## Architecture

```text
User Browser
    ↓
React / Next.js App
    ├── UI Components (Atomic Design)
    ├── State Management (TanStack Query, Context)
    └── Service Layer (API client)
    ↓
FastAPI Backend
```

## Core Modules

- **Dashboard** – KPI cards, recent activity, market overview
- **Marketplace Explorer** – Advanced search, filters, product details
- **Analytics Portal** – Interactive charts (line, bar, heatmap, geo)
- **Recommendations** – Similar products, price‑value suggestions
- **User Profile** – Account settings, saved searches, notifications

## Design Principles

- Mobile‑first responsive layout
- Accessibility (WCAG 2.1 AA)
- Progressive enhancement
- Reusable component library in `frontend/components/`

## Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Data Fetching**: TanStack Query
- **Charts**: Recharts / Apache ECharts
- **Maps**: Leaflet for shipping routes

## Running Locally

```bash
cd frontend
npm install
npm run dev
```
App runs on `http://localhost:3000`.

## Testing

- Unit tests with Jest + React Testing Library
- E2E tests with Playwright (`npm run test:e2e`)

## Building for Production

```bash
npm run build
npm start
```

## Configuration

API base URL and other settings are in `frontend/.env.local`.
```