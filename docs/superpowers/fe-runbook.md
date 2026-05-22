# FE Autonomous Build — Runbook

> **You are an autonomous Claude agent fired by a cron job.** This file is your complete brief. You have no memory from previous ticks. Read this top to bottom, then read `docs/superpowers/fe-progress.md`, then act.

## 1. Project context

This is `my_kiot`, a multi-tenant POS + inventory SaaS. Backend (FastAPI + Postgres) is complete (see [CLAUDE.md](../../CLAUDE.md)). Your job is to build the React frontend autonomously, one phase per cron tick, ~7 ticks total.

**Source design spec:** [docs/superpowers/specs/2026-05-22-fe-orchestration-design.md](specs/2026-05-22-fe-orchestration-design.md) — read it if you need full context. This runbook is the operational version.

**Tech stack (mandatory):** Vite + React 18 + TypeScript + Tailwind CSS + Zustand + react-router-dom + axios + Recharts + dayjs. Tests: Vitest + @testing-library/react + msw.

## 2. Cold-start procedure (every tick, in order)

### 2.1 Read state

Read `docs/superpowers/fe-progress.md`. Parse frontmatter and phase sections. You're looking for:
- `status` in frontmatter (`in_progress` / `complete` / `failed`)
- The first phase with `status: pending` (or `design_failed` / `code_failed` / `deferred` — these are also "next to try")

### 2.2 Termination check

If frontmatter `status` is `complete` OR `failed`, OR all 7 phases have `status: done`:
1. Read `cron_id` from frontmatter
2. Call `CronDelete(id=<cron_id>)`
3. Append a line to the Run Log: `- <ISO timestamp> | termination | All phases done — cron deleted`
4. Set frontmatter `status: complete`
5. Run `git add docs/superpowers/fe-progress.md && git commit -m "FE build: complete"`
6. Stop. Do nothing else.

### 2.3 Token check (best-effort)

Run two trivial probes:
1. `Bash("ls .")` — must succeed and list project root
2. `Read("CLAUDE.md", limit=5)` — must return content

If **either fails**:
- Find next pending phase
- Set its `notes` to `"deferred at <ISO timestamp>: token_check_failed"`
- Append Run Log line: `- <ISO ts> | token_check_failed | skipped tick`
- Commit and stop

### 2.4 Pick next phase

Find the first phase (Phase 0 through Phase 6) whose `status` is `pending`, `design_failed`, `code_failed`, or `deferred`.

If none found but frontmatter `status` is not `complete` → it's a bug; mark frontmatter `status: failed`, log it, commit, stop.

### 2.5 Attempts cap

If selected phase's `attempts` ≥ 3:
- Set frontmatter `status: failed`
- Append Run Log line describing the failed phase
- Call `CronDelete(id=<cron_id>)`
- Commit and stop

### 2.6 Mark phase in_progress

In the selected phase block:
- `status: in_progress`
- `started_at: <ISO timestamp>`
- `attempts: <previous + 1>`

Save the progress file immediately (don't wait until end). Then proceed.

## 3. Execute the 3 steps of the selected phase

For each step, if it raises an exception you cannot recover from, follow Section 4 (failure handling). Otherwise proceed.

### Step 1 — Design

**Do NOT invoke `superpowers:brainstorming`** — its HARD-GATE requires user approval and breaks autonomous flow.

1. Read the phase's row in Section 6 of this runbook (phase definition).
2. Read relevant backend routers using `Grep` on `backend/modules/<module>/router.py` to enumerate endpoints exactly.
3. Read [CLAUDE.md](../../CLAUDE.md) sections relevant to this phase.
4. Produce a design markdown file at `docs/superpowers/specs/2026-05-22-fe-phase{N}-{topic}-design.md` covering:
   - **Routes** (react-router paths)
   - **Components** (file paths, props, responsibility — one paragraph each)
   - **State** (Zustand stores: shape, actions)
   - **API mapping** (table: endpoint → which component/store calls it → request shape → response handling)
   - **Edge cases & error handling**
   - **Test plan** (which behaviors get unit tests)
5. Invoke `superpowers:writing-plans` with the design file as input. It will produce `docs/superpowers/plans/fe-phase{N}-{topic}-plan.md`. (writing-plans is autonomous-mode safe — it writes a file and offers execution choice; you'll proceed directly to Step 2 below regardless of what it offers.)
6. Update the phase in progress.md: `spec_file: <path>`, `plan_file: <path>`.

### Step 2 — Code

1. Read the plan file from Step 1.
2. Execute the plan task-by-task. Use `Write`/`Edit` directly. **Do NOT** dispatch subagents (you're already inside an autonomous tick — nested dispatches blow context).
3. All code under `frontend/src/...`. Phase 0 also creates `frontend/` directory + scaffolding files; later phases assume it exists.
4. After all code is written:
   - Run `cd frontend && npx tsc --noEmit` (skip if Phase 0 hasn't created `tsconfig.json` yet)
   - Fix any type errors before proceeding to tests.
5. Update phase in progress.md: `output_files: [<list of files created/modified>]`.

### Step 3 — Tests

1. For each new component/store/util from Step 2, write a Vitest test file.
2. Mock API calls via MSW handlers under `frontend/src/__tests__/mocks/handlers.ts` (extend, don't replace).
3. Run `cd frontend && npm run test -- --run --reporter=verbose`.
4. Capture pass/fail count.
5. If tests pass → phase `status: done`. If tests fail but ran → phase `status: tests_failing`, also set `done: true` for advancement.

## 4. Failure handling

| Where | Mark | Then |
|---|---|---|
| Token check fail | phase `notes` += deferred reason; phase `status` unchanged (still pending/etc) | commit, stop tick |
| Step 1 (Design) throws | `status: design_failed`, `notes` += error summary | commit, stop tick |
| Step 2 (Code) throws (e.g., tsc errors unresolved, missing file) | `status: code_failed`, `notes` += error summary | commit, stop tick |
| Step 3 setup error (tests cannot run, e.g., vitest config broken) | `status: tests_setup_failed`, `notes` += error | commit, stop tick |
| Step 3 tests run but some fail | `status: tests_failing`, `done: true` | commit, advance — next tick picks Phase N+1 |
| Step 3 all tests pass | `status: done` | commit, advance |
| Same phase fails 3 times | frontmatter `status: failed`, CronDelete | stop permanently |

**Always** end the tick with:
1. Set `finished_at: <ISO timestamp>` on the phase
2. Append a Run Log line: `- <ISO ts> | phase {N} | <result>`
3. `git add` only `docs/superpowers/` and `frontend/`; never stage `backend/`, `alembic/`, etc.

To restrict staging:
```
git add docs/superpowers/fe-progress.md docs/superpowers/specs/ docs/superpowers/plans/ frontend/
git commit -m "FE phase {N}: <topic> — <result>"
```

## 5. Reading & writing progress.md

The file uses YAML frontmatter + Markdown bullets per phase. Pattern:

```markdown
---
build_id: fe-build-2026-05-22
created_at: 2026-05-22T...
cron_id: <id>
total_phases: 7
completed_phases: <int>
status: in_progress
---

# FE Build Progress

## Phase 0 — Setup khung FE
- status: pending
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []
- done: false

## Phase 1 — Auth & Staff
...

# Run Log
- 2026-05-22T... | bootstrap | created
```

**Editing tactic:** use the `Edit` tool with exact string matches on the lines you're changing (e.g., `- status: pending` → `- status: in_progress`). Do NOT regenerate the whole file. Since multiple phases share `- status: pending`, anchor edits with the section header (e.g., include `## Phase 0 — Setup khung FE\n- status: pending` in the old_string to be unique).

## 6. Phase definitions

### Phase 0 — Setup khung FE
**Topic slug:** `setup`
**Endpoints:** none (this builds the API client foundation)
**Output:**
- `frontend/` Vite scaffold: `npm create vite@latest frontend -- --template react-ts` (or equivalent manual setup)
- Install deps: `npm i axios zustand react-router-dom dayjs recharts` and `npm i -D tailwindcss postcss autoprefixer vitest @vitest/coverage-v8 @testing-library/react @testing-library/jest-dom jsdom msw @types/node`
- `tailwindcss init -p` + configure `tailwind.config.js` to scan `src/**/*.{ts,tsx}`
- `src/index.css` with `@tailwind base; components; utilities;`
- `src/api/client.ts` — axios instance + interceptor for JWT refresh (POST `/auth/refresh` when access expires; uses HttpOnly cookie for refresh token)
- `src/stores/authStore.ts` — Zustand store: `user, tenant, accessToken, login(), logout(), setUser()`
- `src/components/AppLayout.tsx` — sidebar + topbar + `<Outlet/>`
- `src/components/ProtectedRoute.tsx` — redirect to `/login` if not authenticated
- `src/components/RoleGate.tsx` — `<RoleGate allow={['OWNER']}>{children}</RoleGate>`
- `src/utils/format.ts` — `formatVND`, `formatDate(Asia/Ho_Chi_Minh)`, `formatQty`
- `src/utils/errors.ts` — map `{error: {code, message, details}}` → user-facing message + toast
- `src/App.tsx` — router with placeholder routes
- `src/__tests__/mocks/handlers.ts` (empty starter), `src/__tests__/setup.ts`, `vitest.config.ts`
- Smoke tests: format utils, error mapper

### Phase 1 — Auth & Staff
**Topic slug:** `auth`
**Endpoints:**
- `POST /api/v1/auth/register` — register shop
- `POST /api/v1/auth/login` — login (handle 429 lockout w/ Vietnamese message)
- `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `PUT /api/v1/auth/change-password`, `GET /api/v1/auth/me`
- Staff: `GET /api/v1/staff`, `POST /api/v1/staff`, `PUT /api/v1/staff/{id}`, `PATCH /api/v1/staff/{id}/(de)activate`
**Pages:** `/login`, `/register`, `/me/change-password`, `/staff` (Owner only)

### Phase 2 — Master Data (Products + Categories + Customers + Suppliers)
**Topic slug:** `master-data`
**Endpoints:**
- Products: `GET/POST/PUT/DELETE /api/v1/products`, `GET /api/v1/products/{id}`, `GET /api/v1/products/search?q=`, `GET /api/v1/products/barcode/{code}`
- Categories: `GET/POST/PUT/DELETE /api/v1/categories` (tree, 2-level)
- Customers: `GET/POST/PUT/DELETE /api/v1/customers`, `GET /api/v1/customers/{id}` (detail incl. history), `GET /api/v1/customers/phone/{phone}`
- Suppliers: `GET/POST/PUT/DELETE /api/v1/suppliers`, `GET /api/v1/suppliers/{id}`
**Pages:** `/products`, `/products/new`, `/products/:id/edit`, `/products/:id`, `/categories`, `/customers`, `/customers/new`, `/customers/:id`, `/suppliers`
**Shared components:** `ProductPicker`, `CustomerQuickSearch` (used in Phase 4)

### Phase 3 — Inventory & Goods Receipts
**Topic slug:** `inventory`
**Endpoints:**
- Goods receipts: `GET/POST/PUT /api/v1/goods-receipts`, `GET /api/v1/goods-receipts/{id}`, `POST /api/v1/goods-receipts/{id}/complete`, `POST /api/v1/goods-receipts/{id}/cancel`
- Inventory: `GET /api/v1/inventory`, `GET /api/v1/inventory/low-stock`, `GET /api/v1/inventory/{product_id}/movements`, `POST /api/v1/inventory/adjustments`, `GET /api/v1/inventory/adjustments`
**Pages:** `/goods-receipts`, `/goods-receipts/new`, `/goods-receipts/:id`, `/inventory`, `/inventory/low-stock`, `/inventory/:productId/movements`, `/inventory/adjustments` (Owner)

### Phase 4 — POS Sales
**Topic slug:** `pos-sales`
**Endpoints:**
- `POST /api/v1/invoices`, `GET /api/v1/invoices`, `GET /api/v1/invoices/drafts`, `GET /api/v1/invoices/{id}`, `PUT /api/v1/invoices/{id}`, `POST /api/v1/invoices/{id}/complete`, `POST /api/v1/invoices/{id}/cancel`
**Pages:** `/pos` (full-screen POS), `/invoices`, `/invoices/:id`
**Key UX:** barcode listener (keyboard event capture), product autocomplete, cart with DECIMAL qty (kg/lạng support), multi-payment (CASH/BANK/MOMO/VNPAY), customer quick-pick (phone), receipt print (`@media print` CSS, 80mm thermal), draft hold/resume list. Disable Complete button immediately after click (anti double-spend, per backlog #7 workaround).

### Phase 5 — Reports
**Topic slug:** `reports`
**Endpoints:**
- `GET /api/v1/reports/dashboard`, `GET /api/v1/reports/revenue?from=&to=&group_by=`, `GET /api/v1/reports/top-products`, `GET /api/v1/reports/profit` (Owner), `GET /api/v1/reports/stock-summary`
**Pages:** `/dashboard` (landing after login), `/reports/revenue`, `/reports/top-products`, `/reports/profit`, `/reports/stock-summary`
**Charts:** Recharts (line for revenue, bar for top products).

### Phase 6 — Polish
**Topic slug:** `polish`
**No new endpoints. Output:**
- Responsive tweaks for tablet (1024×768) — POS specifically
- Empty states + skeleton loaders for all list views
- Keyboard shortcuts on POS: F2 = focus product search, F9 = open payment dialog, Esc = cancel current, F4 = hold invoice
- Top-level `ErrorBoundary` component, wrap router
- `public/manifest.webmanifest` + icons for basic PWA installability

## 7. Conventions

- **Language:** UI text in Vietnamese (matching CLAUDE.md examples). Code/comments in English where they exist (but per CLAUDE.md default = no comments).
- **Tailwind:** utility classes inline; no separate CSS modules.
- **Routing:** `react-router-dom` v6 with nested routes; `AppLayout` is the root layout for authenticated routes.
- **State:** Per-domain Zustand stores in `src/stores/` (authStore, posStore, etc.). Don't put everything in one store.
- **API errors:** Always go through `utils/errors.ts` to display Vietnamese-friendly toast. Detail JSON from BE → keep raw `details` for forms (field-level errors).
- **Tenant isolation:** Backend handles it via JWT — frontend just sends Authorization header. Don't pass `tenant_id` from frontend ever.
- **Commit style:** `FE phase N: <topic> — <result>` for autonomous commits.

## 8. After everything

When Section 2.2 termination triggers, the build is done. Acceptance criteria (verify before declaring complete in the final commit message):

- [ ] `cd frontend && npm run dev` starts the dev server without errors (can't run automated — leave it to user)
- [ ] `cd frontend && npx tsc --noEmit` passes
- [ ] `cd frontend && npm run test -- --run` runs (some failures acceptable per phase-level tracking)
- [ ] Routes `/login`, `/dashboard`, `/products`, `/customers`, `/inventory`, `/pos`, `/invoices`, `/reports/revenue` are reachable in router config (smoke check via grep)

If any of these fail at termination check time, mark frontmatter `status: completed_with_warnings` instead of `complete`, but still CronDelete.
