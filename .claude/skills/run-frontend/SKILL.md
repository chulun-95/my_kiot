---
name: run-frontend
description: Use when launching, building, or previewing the React frontend for this project. Triggers on "build FE", "chạy FE", "start frontend", "xem FE", or any /run invocation on this repo.
---

# Run Frontend

## Overview

React 18 + Vite + TypeScript + Tailwind. Dev server proxies `/api` → `http://localhost:8000` (FastAPI backend).

## Commands

| Goal | Command | Notes |
|------|---------|-------|
| Dev server | `cd frontend && npm run dev` | Port **5173**. Hot-reload. |
| Dev + LAN access | `cd frontend && npm run dev -- --host` | Exposes 0.0.0.0 — useful for mobile testing. |
| Production build | `cd frontend && npm run build` | TypeScript check → Vite bundle → `dist/` |
| Preview build | `cd frontend && npm run preview` | Serves `dist/` locally to verify prod output. |
| Lint | `cd frontend && npm run lint` | ESLint |

## Backend dependency

API calls go through Vite proxy — no CORS setup needed during dev. Backend must be running at `http://localhost:8000` for any API screen to work. Frontend-only UI (login page layout, static mockups) loads fine without backend.

## Quick start

```bash
cd frontend
npm run dev
# Open http://localhost:5173
```

## Build output

`dist/` is served by Nginx in production. No path prefix — deployed at site root.
