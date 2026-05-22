# FE Autonomous Build — Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the autonomous FE build orchestration: write the runbook file (cold-start instructions for the per-tick agent), initialize the state file with 7 pending phases, schedule the hourly cron job, then immediately dispatch Phase 0 (Setup) without waiting for the first cron tick.

**Architecture:** Bootstrap is a pure setup sequence run inline in the current Claude session. The runbook file is the autonomous agent's only memory between ticks; it must be fully self-sufficient. After this bootstrap, every hour the cron fires a fresh Claude session that reads the runbook + progress file and advances the build by one phase.

**Tech Stack:** Filesystem (markdown), `CronCreate` tool (in-process scheduler, durable=true persists to `.claude/scheduled_tasks.json`), git for commits, `Agent` tool (subagent dispatch) for Phase 0 immediate trigger.

**Source spec:** [docs/superpowers/specs/2026-05-22-fe-orchestration-design.md](../specs/2026-05-22-fe-orchestration-design.md)

---

## Files in this plan

- **Create:** `docs/superpowers/fe-runbook.md` — agent's per-tick instructions (~300 lines, self-contained)
- **Create:** `docs/superpowers/fe-progress.md` — state file with 7 phase entries
- **Modify:** `docs/superpowers/fe-progress.md` — fill in `cron_id` after CronCreate returns
- **Tool calls:** `CronCreate` (schedules hourly), `Agent` (Phase 0 immediate kickoff)
- **No code files created in this plan.** Phase 0 (Vite scaffold etc.) is executed by the dispatched subagent following the runbook; it produces `frontend/` contents.

---

## Task 1: Write the runbook file

**Files:**
- Create: `docs/superpowers/fe-runbook.md`

The runbook is the autonomous agent's complete instructions. Each cron tick spawns a fresh Claude session with no memory; it reads only this file + `fe-progress.md` to know what to do. Must be fully self-sufficient (no "see other docs" without inlining the essentials).

- [ ] **Step 1.1: Write the runbook**

Write the file with exactly the content below:

````markdown
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
3. `git add -A && git commit -m "FE phase {N}: <topic> — <result>"` (use `-A` only inside `frontend/` and `docs/superpowers/`; never stage `backend/`, `alembic/`, etc.)

To restrict staging:
```
git add docs/superpowers/fe-progress.md docs/superpowers/specs/ docs/superpowers/plans/ frontend/
git commit -m "..."
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

**Editing tactic:** use the `Edit` tool with exact string matches on the lines you're changing (e.g., `- status: pending` → `- status: in_progress`). Do NOT regenerate the whole file.

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
````

- [ ] **Step 1.2: Verify file exists and is well-formed**

Run: `wc -l docs/superpowers/fe-runbook.md`
Expected: ≥ 250 lines.

Run: `grep -c "## " docs/superpowers/fe-runbook.md`
Expected: ≥ 8 (sections 1-8).

- [ ] **Step 1.3: Commit**

```bash
git add docs/superpowers/fe-runbook.md
git commit -m "docs: FE autonomous build runbook (per-tick agent instructions)"
```

---

## Task 2: Create the initial progress file

**Files:**
- Create: `docs/superpowers/fe-progress.md`

- [ ] **Step 2.1: Write the progress file**

Write the file with exactly the content below. The `cron_id` placeholder `<TO_BE_FILLED>` will be replaced in Task 4.

```markdown
---
build_id: fe-build-2026-05-22
created_at: 2026-05-22T00:00:00+07:00
cron_id: <TO_BE_FILLED>
total_phases: 7
completed_phases: 0
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
- status: pending
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []
- done: false

## Phase 2 — Master Data (Products + Categories + Customers + Suppliers)
- status: pending
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []
- done: false

## Phase 3 — Inventory & Goods Receipts
- status: pending
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []
- done: false

## Phase 4 — POS Sales
- status: pending
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []
- done: false

## Phase 5 — Reports
- status: pending
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []
- done: false

## Phase 6 — Polish
- status: pending
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []
- done: false

# Run Log
- 2026-05-22T00:00:00+07:00 | bootstrap | progress file initialized; cron not yet scheduled
```

- [ ] **Step 2.2: Verify file is well-formed**

Run: `grep -c "^## Phase " docs/superpowers/fe-progress.md`
Expected: `7`

Run: `grep -c "^- status: pending" docs/superpowers/fe-progress.md`
Expected: `7`

- [ ] **Step 2.3: Commit (with cron_id placeholder still in file)**

```bash
git add docs/superpowers/fe-progress.md
git commit -m "docs: FE build progress state file (7 phases pending)"
```

---

## Task 3: Schedule the hourly cron job

**Files:** none (tool call only)

- [ ] **Step 3.1: Call CronCreate**

Use the `CronCreate` tool with exactly these arguments:

```
cron: "13 * * * *"
durable: true
recurring: true
prompt: |
  <<autonomous-loop>>

  You are the FE autonomous build agent. Your COMPLETE instructions are in
  docs/superpowers/fe-runbook.md (in the current working directory).

  Procedure:
  1. Read docs/superpowers/fe-runbook.md top-to-bottom.
  2. Read docs/superpowers/fe-progress.md.
  3. Follow runbook Section 2 (cold-start procedure) exactly.
  4. If a phase is selected, execute its 3 steps per runbook Section 3.
  5. Always end with commit + exit (runbook Section 4).

  Project: my_kiot POS system (see CLAUDE.md). You are running in
  c:\Users\VuongNV\Downloads\my_kiot. Frontend stack: Vite + React 18 +
  TS + Tailwind + Zustand. Backend is already done; do NOT modify backend/.
```

Expected: tool returns a job id like `cron-xxxxxxxx`. **Record this id** — you'll need it in Task 4.

- [ ] **Step 3.2: Verify cron is scheduled**

Use `CronList` tool with no arguments.

Expected: at least one entry whose `cron` field is `"13 * * * *"`.

---

## Task 4: Record the cron_id in progress.md

**Files:**
- Modify: `docs/superpowers/fe-progress.md`

- [ ] **Step 4.1: Replace the placeholder**

Use the `Edit` tool with:
- `old_string`: `cron_id: <TO_BE_FILLED>`
- `new_string`: `cron_id: <the actual id from Task 3.1>`

- [ ] **Step 4.2: Append Run Log entry**

Use the `Edit` tool to append a line at the end of the file. Old string:

```
- 2026-05-22T00:00:00+07:00 | bootstrap | progress file initialized; cron not yet scheduled
```

New string (replace `<ts>` with current ISO timestamp in `+07:00` offset; replace `<cron_id>` with the actual id):

```
- 2026-05-22T00:00:00+07:00 | bootstrap | progress file initialized; cron not yet scheduled
- <ts> | bootstrap | cron scheduled (id=<cron_id>, schedule=13 * * * *, durable=true)
```

- [ ] **Step 4.3: Verify**

Run: `grep "cron_id:" docs/superpowers/fe-progress.md`
Expected: shows the real id, not `<TO_BE_FILLED>`.

- [ ] **Step 4.4: Commit**

```bash
git add docs/superpowers/fe-progress.md
git commit -m "chore: record cron_id in FE build progress state"
```

---

## Task 5: Dispatch Phase 0 immediately (don't wait for first cron tick)

**Files:** none (Agent tool dispatch); subagent will create `frontend/` etc.

The user explicitly chose "run Phase 0 ngay lập tức". Per the runbook, the subagent will:
- Read the runbook + progress file
- Pick Phase 0 (the first pending)
- Run the 3 steps (Design → Code → Tests)
- Update progress.md
- Commit with message `FE phase 0: setup — done` (or failure variant)

After this task, the cron will pick up Phase 1 at the next `:13` minute and continue every hour.

- [ ] **Step 5.1: Dispatch the Phase 0 subagent**

Use the `Agent` tool with:
- `subagent_type`: `general-purpose`
- `description`: `FE Phase 0 (Setup) autonomous run`
- `prompt`:

```
You are the FE autonomous build agent for the my_kiot project, dispatched manually for Phase 0 (Setup khung FE) — do NOT wait for cron.

Procedure (MUST follow exactly):

1. Read docs/superpowers/fe-runbook.md top-to-bottom.
2. Read docs/superpowers/fe-progress.md.
3. Follow runbook Section 2 (cold-start procedure):
   - Skip termination check (you know Phase 0 is pending).
   - Run token check (Section 2.3).
   - Select Phase 0 specifically (do not run any other phase even if Phase 0 status changes due to a race — you are Phase 0).
   - Mark Phase 0 in_progress with attempts +1.
4. Execute Phase 0's 3 steps per runbook Section 3:
   - Step 1 Design: produce docs/superpowers/specs/2026-05-22-fe-phase0-setup-design.md + invoke writing-plans for docs/superpowers/plans/fe-phase0-setup-plan.md
   - Step 2 Code: create frontend/ via Vite, install deps, scaffold src/api/client.ts, stores/authStore.ts, components/AppLayout.tsx, ProtectedRoute.tsx, RoleGate.tsx, utils/format.ts, utils/errors.ts, App.tsx with router, vitest config + setup
   - Step 3 Tests: write smoke tests for format utils and error mapper; run them
5. Update docs/superpowers/fe-progress.md with results (Phase 0 status=done or tests_failing/code_failed/design_failed as appropriate per runbook Section 4).
6. Commit per runbook end-of-tick rules: `git add docs/superpowers/fe-progress.md docs/superpowers/specs/ docs/superpowers/plans/ frontend/ && git commit -m "FE phase 0: setup — <result>"`.

Critical constraints:
- DO NOT modify backend/, alembic/, tests/, or any file outside frontend/ and docs/superpowers/.
- DO NOT dispatch nested subagents — you execute Step 2 inline with Write/Edit tools.
- DO NOT invoke superpowers:brainstorming (HARD-GATE blocks autonomous mode); produce the design markdown directly.
- DO invoke superpowers:writing-plans for the per-phase plan file in Step 1.
- DO commit at the end regardless of success/failure (so the next cron tick has fresh state).

Working directory: c:\Users\VuongNV\Downloads\my_kiot
Stack reminder: Vite + React 18 + TypeScript + Tailwind + Zustand + react-router-dom + axios + Recharts + dayjs; tests via Vitest + RTL + MSW.
```
- `run_in_background`: `false` (we want the result before declaring bootstrap done)

- [ ] **Step 5.2: Verify Phase 0 outcome**

After subagent returns, read `docs/superpowers/fe-progress.md` and confirm:
- Phase 0 `status` is `done` or `tests_failing` (acceptable) — NOT `pending`
- Phase 0 `output_files` lists files under `frontend/`
- Run Log has an entry for Phase 0

If `status` is `design_failed` / `code_failed`: report to user, do not dispatch retries (cron will retry next tick).

- [ ] **Step 5.3: Bootstrap complete report**

Print a summary to the user covering:
- Cron job ID and schedule
- Phase 0 result (done / failed)
- Next cron tick wall-clock time (next `:13`)
- Reminder: Claude Code must stay open for cron to fire

---

## Self-Review

**Spec coverage check** (against [2026-05-22-fe-orchestration-design.md](../specs/2026-05-22-fe-orchestration-design.md)):

| Spec section | Covered by |
|---|---|
| §3 Architecture (cron + autonomous loop) | Task 1 (runbook §2-3) + Task 3 (CronCreate) |
| §4 Artifacts layout (docs/superpowers/...) | Task 1, Task 2 create the root files; agent creates per-phase files |
| §5 State file schema | Task 2 (exact template) |
| §6 Cron details (`13 * * * *`, durable=true) | Task 3 (exact args) |
| §7 Loop algorithm | Task 1 runbook §2 (cold-start procedure) |
| §8 Phase breakdown | Task 1 runbook §6 (all 7 phases enumerated with endpoints) |
| §9 Tech stack | Task 1 runbook §1 + §7 |
| §10 Step contracts | Task 1 runbook §3 (per-step instructions) |
| §11 Failure handling | Task 1 runbook §4 (table) |
| §12 Token check | Task 1 runbook §2.3 |
| §13 Lifecycle (Phase 0 immediate) | Task 5 (Agent dispatch) |
| §14 Risks (Claude must stay open) | Task 5.3 (reminder in summary) |
| §15 Acceptance criteria | Task 1 runbook §8 |

**Placeholder scan:** No TBD / fill-in-later / "implement appropriately" in plan content. The `<TO_BE_FILLED>` in Task 2 is intentional and resolved in Task 4.

**Type consistency:** `cron_id` is the same identifier in CronCreate output, progress.md frontmatter, and the CronDelete call in runbook §2.2. Phase status enum (`pending` / `in_progress` / `done` / `design_failed` / `code_failed` / `tests_setup_failed` / `tests_failing` / `deferred`) is consistent between progress.md template (Task 2), failure table (runbook §4), and selection logic (runbook §2.4).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-22-fe-orchestration-bootstrap.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Note: Task 5 itself dispatches a subagent for Phase 0, so option 1 means *nested* subagents (one to execute the task, one for Phase 0 inside it). This is fine because Task 5 is a single Agent call, not a long subagent run.

**2. Inline Execution** — execute tasks 1-5 in this current session using executing-plans, batch execution with checkpoints for review. Task 5's Agent dispatch still happens, just from the main session.

Recommend **Inline Execution** for this plan because:
- Only 5 tasks total
- Tasks 1-4 are pure file writes + 1 tool call (low ambiguity)
- Task 5 already dispatches a subagent internally for Phase 0
- Less nested-subagent overhead
