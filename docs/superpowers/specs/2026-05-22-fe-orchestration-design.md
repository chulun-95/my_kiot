# FE Autonomous Build Orchestration — Design Spec

- **Date:** 2026-05-22
- **Owner:** vuongnv95work@gmail.com
- **Project:** my_kiot (POS + Inventory, multi-tenant SaaS)
- **Status:** Approved (brainstorming → writing-plans)

## 1. Goal

Tự động build phần Frontend cho POS system qua **7 phase**, mỗi phase chạy cách nhau **1 giờ**, không cần user approve giữa các phase. Mỗi phase bao gồm 3 step:

1. **Design:** brainstorm UI + map API → ghi spec file → writing-plans → ghi plan file
2. **Code:** đọc plan, scaffold/edit components, wire `api/client.ts`, tích hợp endpoints
3. **Test:** viết Vitest + React Testing Library + MSW unit tests, chạy chúng

Trước mỗi tick, agent kiểm tra "token còn không" (best-effort). Nếu fail → skip, retry tick sau.

## 2. Context (Backend hiện trạng)

Backend MVP đã hoàn tất (xem [CLAUDE.md](../../../CLAUDE.md)):

- 6 modules: auth, product, customer, sales, inventory, report — tất cả routers mount trong [main.py](../../../backend/main.py)
- 156 tests collected, migrations 001 + 002
- Endpoints khớp đầy đủ với spec (trừ `/products/import` defer theo backlog #3)

Frontend chưa tồn tại (`frontend/` folder chưa có). Stack mục tiêu (per CLAUDE.md): **Vite + React 18 + TypeScript + Tailwind CSS + Zustand**.

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ CronCreate job: cron "13 * * * *", durable=true             │
│   prompt = autonomous-loop sentinel + runbook reference     │
└────────────┬────────────────────────────────────────────────┘
             │ fires hourly (Claude Code phải đang chạy)
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Autonomous loop tick (fresh Claude session)                 │
│ 1. Read fe-progress.md                                      │
│ 2. If done → CronDelete self + log COMPLETE + exit          │
│ 3. Token check (ping Bash + Read) — fail → mark deferred    │
│ 4. Mark next phase in_progress                              │
│ 5. Run 3 steps sequentially: design → code → test           │
│ 6. Update progress.md, git commit, exit                     │
└─────────────────────────────────────────────────────────────┘
```

## 4. Artifacts layout

```
docs/superpowers/
├── specs/
│   ├── 2026-05-22-fe-orchestration-design.md     ← THIS file (master)
│   ├── 2026-05-22-fe-phase0-setup-design.md      ← agent ghi trong tick phase 0
│   ├── 2026-05-22-fe-phase1-auth-design.md
│   ├── 2026-05-22-fe-phase2-master-data-design.md
│   ├── 2026-05-22-fe-phase3-inventory-design.md
│   ├── 2026-05-22-fe-phase4-pos-sales-design.md
│   ├── 2026-05-22-fe-phase5-reports-design.md
│   └── 2026-05-22-fe-phase6-polish-design.md
├── plans/
│   ├── fe-phase0-setup-plan.md                   ← writing-plans output
│   ├── fe-phase1-auth-plan.md
│   ├── ... (1 plan / phase)
│   └── fe-phase6-polish-plan.md
└── fe-progress.md                                 ← STATE — agent đọc/ghi
```

## 5. State file — `fe-progress.md` schema

Markdown checklist với metadata YAML frontmatter. Agent parse bằng pattern matching đơn giản.

```markdown
---
build_id: fe-build-2026-05-22
created_at: 2026-05-22T00:00:00+07:00
cron_id: <returned by CronCreate>
total_phases: 7
completed_phases: 0
status: in_progress    # in_progress | complete | failed
---

# FE Build Progress

## Phase 0 — Setup khung FE
- status: pending           # pending | in_progress | done | design_failed | code_failed | tests_failing | deferred
- started_at: null
- finished_at: null
- attempts: 0
- spec_file: null
- plan_file: null
- output_files: []
- notes: []

## Phase 1 — Auth & Staff
- status: pending
- ...

## Phase 2 — Master Data (Products + Categories + Customers + Suppliers)
- status: pending
- ...

## Phase 3 — Inventory & Goods Receipts
...

## Phase 4 — POS Sales
...

## Phase 5 — Reports
...

## Phase 6 — Polish
...

# Run Log
(timestamp, tick_id, event) — append-only
```

## 6. Cron details

| Field | Value | Rationale |
|---|---|---|
| `cron` | `"13 * * * *"` | Mỗi giờ, off-minute (tránh fleet collision per CronCreate guidance) |
| `durable` | `true` | Persist `.claude/scheduled_tasks.json`, sống qua restart Claude |
| `recurring` | `true` | Fire mỗi giờ cho đến khi xong hoặc 7 ngày |
| Lifetime | 7 days max | 7 phase × 1h + retry buffer ≪ 7d, dư |
| Idle requirement | Cron chỉ fire khi REPL idle | User nên không giữ tool calls treo lúc gần `:13` |

## 7. Autonomous loop algorithm (pseudo-code)

```python
def autonomous_tick():
    progress = read("docs/superpowers/fe-progress.md")

    # 2. Termination check
    if progress.status == "complete" or progress.completed_phases == 7:
        cron_delete(progress.cron_id)
        append_log(progress, "BUILD COMPLETE")
        git_commit("FE build: complete")
        return

    # 3. Best-effort token check
    try:
        bash("ls")            # trivial process test
        read(any_existing_file)  # trivial Read tool test
    except Exception as e:
        next_phase = find_first_pending(progress)
        mark(next_phase, status="deferred", note=f"token_check_failed: {e}")
        save_progress(progress)
        return

    # 4. Find next phase to run
    phase = find_first_pending_or_failed(progress)
    if phase is None:
        # shouldn't happen — already checked complete
        return

    # Stop condition: too many attempts
    if phase.attempts >= 3:
        progress.status = "failed"
        cron_delete(progress.cron_id)
        append_log(progress, f"BUILD FAILED at {phase.name} after 3 attempts")
        save_progress(progress)
        return

    mark(phase, status="in_progress", started_at=now(), attempts=phase.attempts + 1)
    save_progress(progress)

    # 5. Run 3 steps
    try:
        spec_file = step_design(phase)         # brainstorming + writing-plans
        phase.spec_file = spec_file
        phase.plan_file = derive_plan_path(phase)

        output_files = step_code(phase)        # executing-plans or direct edit
        phase.output_files = output_files

        test_result = step_tests(phase)        # Vitest run
        if test_result.passed:
            mark(phase, status="done", finished_at=now())
            progress.completed_phases += 1
        else:
            mark(phase, status="tests_failing", finished_at=now(),
                 note=f"{test_result.failed_count} tests failing")
            progress.completed_phases += 1     # still advance — user reviews failing tests

    except DesignError as e:
        mark(phase, status="design_failed", note=str(e))
    except CodeError as e:
        mark(phase, status="code_failed", note=str(e))

    # 6. Commit + exit
    save_progress(progress)
    git_commit(f"FE phase {phase.number}: {phase.topic}")
    # cron fires again next hour
```

## 8. Phase breakdown

| # | Phase | Endpoints / Modules BE | Output FE chính |
|---|---|---|---|
| 0 | Setup khung FE | — | `frontend/` Vite scaffold, deps installed, Tailwind config, `api/client.ts` (axios + JWT refresh interceptor), `authStore` (Zustand), `AppLayout`, `ProtectedRoute`, `RoleGate`, format/error utils, base routing |
| 1 | Auth & Staff (UC-A) | `/auth/*` (register, login, refresh, logout, change-password, me) + `/staff/*` | `/login`, `/register`, `/me/change-password`, `/staff` (list + create + activate/deactivate, Owner gate) |
| 2 | Master Data (UC-P + UC-C) | `/products/*` (incl. search, barcode), `/categories/*`, `/customers/*` (incl. phone lookup), `/suppliers/*` | `/products` (list/new/edit/detail), `/categories` (tree 2-level), `/customers` (list/detail/CRUD), `/suppliers`; shared `ProductPicker`, `CustomerQuickSearch` |
| 3 | Inventory (UC-I) | `/goods-receipts/*`, `/inventory/*`, `/inventory/adjustments` | `/goods-receipts` (CRUD + complete/cancel), `/inventory` (list + low-stock + `:pid/movements` kardex), `/inventory/adjustments` (Owner) |
| 4 | POS Sales (UC-S) | `/invoices/*` (incl. drafts, complete, cancel) | `/pos` full-screen (barcode + autocomplete + cart + multi-payment + draft/hold + customer pick + receipt print), `/invoices` history + detail + cancel |
| 5 | Reports (UC-R) | `/reports/*` | `/dashboard`, `/reports/revenue` (line/bar chart), `/reports/top-products`, `/reports/profit` (Owner gate), `/reports/stock-summary` — using **Recharts** |
| 6 | Polish | — | Responsive tablet (1024×768), empty states, skeleton loaders, keyboard shortcuts cho POS (F2, F9...), error boundary, PWA manifest cơ bản |

## 9. Tech & testing stack (chuẩn xác)

- **App:** Vite, React 18, TypeScript 5, Tailwind CSS 3, Zustand 4, react-router-dom 6, axios, Recharts, dayjs
- **Tests:** Vitest, @testing-library/react, @testing-library/jest-dom, msw (mock service worker)
- **Lint/format:** ESLint + Prettier (default Vite TS template)
- **Coverage:** ≥ 70% mỗi phase, đo bằng `vitest run --coverage`
- **Acceptance:** mỗi phase phải `tsc --noEmit` pass + `vitest run` không lỗi runtime (tests_failing chấp nhận, tests_erroring không)

## 10. Step type contracts

### Step 1 — Design
- **Input:** Phase definition (từ section 8), endpoints liên quan (từ CLAUDE.md), [main.py](../../../backend/main.py) router listing
- **Process:** Agent chạy autonomous, **không invoke `superpowers:brainstorming`** (skill này HARD-GATE chờ user approval, không tương thích autonomous mode). Thay vào đó, agent emulate brainstorming-style analysis:
  1. Đọc CLAUDE.md + router files liên quan để liệt kê endpoints
  2. Chốt: routes, components, Zustand store shape, API contract mapping (endpoint → component prop/store action), edge cases
  3. Ghi spec file `docs/superpowers/specs/2026-05-22-fe-phaseN-<topic>-design.md`
  4. Invoke `superpowers:writing-plans` để ghi `docs/superpowers/plans/fe-phaseN-<topic>-plan.md` (writing-plans an toàn trong autonomous mode vì output là file, không yêu cầu approval gate giữa chừng)
- **Output:** spec file + plan file paths, ghi vào progress.md

### Step 2 — Code
- **Input:** plan file từ step 1
- **Process:**
  1. Invoke `superpowers:executing-plans` (hoặc direct edit nếu plan trivial)
  2. Tạo/sửa files dưới `frontend/src/`
  3. Đảm bảo `tsc --noEmit` pass
- **Output:** List file đã tạo/sửa, ghi vào progress.md

### Step 3 — Tests
- **Input:** Output files của step 2
- **Process:**
  1. Viết tests theo principle: 1 test file / component hoặc 1 test file / store
  2. Mock API qua MSW handlers ở `frontend/src/__tests__/mocks/`
  3. Chạy `npm run test -- --run` (single run, không watch)
  4. Capture pass/fail count
- **Output:** test files + run summary, ghi vào progress.md

## 11. Failure handling

| Tình huống | Hành vi | Lý do |
|---|---|---|
| Token check fail | Mark phase `deferred`, exit | Tick sau retry tự nhiên |
| Step 1 (design) fail | Mark `design_failed`, exit | Phase không advance; tick sau retry |
| Step 2 (code) fail | Mark `code_failed`, exit (không chạy test) | Tick sau retry; có spec/plan rồi nên không mất công |
| Step 3 (test) error (test setup hỏng, không chạy được) | Mark `tests_setup_failed` | Phân biệt với code_failed: code chạy được nhưng test infra broken |
| Step 3 (test) fail (tests run nhưng có fail) | Mark `tests_failing`, `done=true`, advance | Cho phép tiếp tục; user review failed tests |
| ≥ 3 attempts cùng 1 phase | `progress.status = failed`, CronDelete, dừng | Tránh loop vô hạn |
| Git commit fail | Log error, exit (không update progress) | Tránh state inconsistency |

## 12. Token check (best-effort)

Không có API trực tiếp để query Anthropic API budget. Triển khai:

```
1. Run Bash("ls .") — confirm process tool works
2. Run Read("CLAUDE.md", limit=5) — confirm Read tool works
3. If both succeed → continue
4. If either fails với "rate limit" / "quota" / "unauthorized" → mark deferred
```

Nếu thật sự bị Anthropic rate-limit, cron tick sẽ fail tự nhiên trong khi đang gọi LLM → exception ở agent → next tick retry. Token check chỉ catch các trường hợp environment lỗi sớm.

## 13. Lifecycle & termination

- **Start:** Sau khi spec này approved và writing-plans tạo xong implementation plan:
  1. Tạo file `docs/superpowers/fe-progress.md` initial (7 phase status=pending)
  2. Call `CronCreate(cron="13 * * * *", durable=true, prompt=<autonomous-loop sentinel + runbook>)`
  3. Lưu `cron_id` vào progress.md frontmatter
  4. **Run Phase 0 ngay lập tức** (không đợi tick đầu) — user đã chọn option này
- **Tiến triển:** Mỗi giờ 1 phase. Hoàn thành toàn bộ ≈ 7-8 giờ (7 phase × 1h, có thể thêm 1-2 giờ buffer cho retry)
- **End:** Phase 6 done → autonomous tick phát hiện all done → CronDelete + ghi "BUILD COMPLETE" + final commit
- **Hard fail:** Bất kỳ phase nào fail ≥ 3 lần → BUILD FAILED, CronDelete, dừng. User phải intervene manual.

## 14. Risks & open issues

| Risk | Mitigation |
|---|---|
| Claude Code không chạy lúc cron fire | User được cảnh báo phải giữ Claude open. `durable: true` giúp khi restart. |
| Một phase quá lớn vượt context (đặc biệt Phase 4 POS) | State track ở phase level — nếu code step ngốn quá nhiều context, kết thúc tick với mark in_progress; tick sau resume. Cần plan file đủ chi tiết để pick up dở dang. |
| `npm install` fail (network/proxy) | Phase 0 retry tự nhiên qua attempts counter. Hard fail sau 3 lần. |
| Brainstorming skill HARD-GATE không tương thích autonomous | Agent KHÔNG invoke `superpowers:brainstorming` trực tiếp. Step 1 tự emulate phân tích design rồi gọi writing-plans (xem section 10 Step 1). |
| Agent không thể AskUserQuestion mid-tick | Agent phải tự quyết mọi lựa chọn dựa trên spec này + CLAUDE.md + sensible defaults. Nếu thật sự bí → mark `code_failed` với note chi tiết, để user can thiệp ngoài. |
| Cron 7-day auto-expire | 7 phase × 1h + retry buffer < 30h ≪ 7d. Không vấn đề. |
| Conflict với tests BE đang chạy | FE build chỉ thay đổi dưới `frontend/`. BE tests vẫn pass. |

## 15. Acceptance criteria (overall)

Sau khi cron job tự terminate với `status: complete`:

- [ ] `frontend/` tồn tại với 7 phase output đã merge
- [ ] `cd frontend && npm run dev` start dev server không lỗi
- [ ] `cd frontend && tsc --noEmit` pass
- [ ] `cd frontend && npm run test -- --run` chạy được (≥ 70% tests pass)
- [ ] Routes chính accessible: `/login`, `/dashboard`, `/products`, `/customers`, `/inventory`, `/pos`, `/invoices`, `/reports/revenue`
- [ ] `docs/superpowers/fe-progress.md` shows all 7 phases done với output files
- [ ] Git history có 7+ commits với message `FE phase N: <topic>`

## 16. Out of scope

- BE changes (đã frozen cho phase 1 MVP)
- E2E tests (Playwright/Cypress) — chỉ unit + integration trong Vitest
- Production deploy / Nginx config
- Mobile app / PWA offline mode (defer theo backlog)
- i18n đầy đủ (hardcode tiếng Việt)
- Storybook / visual regression

## 17. Next step

Invoke `superpowers:writing-plans` skill để tạo implementation plan chi tiết về cách bootstrap state file + CronCreate + Phase 0 immediate trigger.
