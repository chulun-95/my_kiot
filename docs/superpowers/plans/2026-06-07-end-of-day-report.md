# Báo cáo cuối ngày (End-of-Day) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Báo cáo cuối ngày read-only theo NGÀY (mốc Asia/Ho_Chi_Minh): tồn quỹ đầu/cuối ngày + tổng thu/chi theo từng phương thức (CASH/BANK_TRANSFER/EWALLET) + doanh thu bán hàng (trừ trả hàng) + số hóa đơn. Suy từ `cash_transactions` + `invoices` + `return_orders`. OWNER-only. KHÔNG bảng mới, KHÔNG migration.

**Architecture:** Hàm `end_of_day(db, tenant_id, business_date)` trong `report/service.py`. Mốc ngày dùng **VN timezone (UTC+7)** thay vì UTC (sửa bug ngày). Số dư append-only: opening = lũy kế trước đầu ngày, closing = opening + thu − chi (chỉ phiếu ACTIVE).

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, pytest (SQLite), React 18 + TS + Vitest + MSW.

**Quyết định (Gate 1):** read-only; fix timezone VN; KHÔNG "tiền thực đếm/chênh lệch" (thuộc Kết ca — defer). Doanh thu cuối ngày = doanh thu hóa đơn − trả hàng trong ngày (nhất quán với báo cáo doanh thu).

---

### Task 1: Backend — schemas + service (VN timezone) + tests

**Files:**
- Modify: `backend/modules/report/schemas.py`
- Modify: `backend/modules/report/service.py`
- Test: `tests/test_report.py`

- [ ] **Step 1: schemas** — thêm vào `backend/modules/report/schemas.py`:

```python
class EodMethodRow(BaseModel):
    method: str
    opening: Decimal
    total_in: Decimal
    total_out: Decimal
    closing: Decimal


class EndOfDayResponse(BaseModel):
    business_date: date
    by_method: list[EodMethodRow]
    opening_total: Decimal
    in_total: Decimal
    out_total: Decimal
    closing_total: Decimal
    sales_revenue: Decimal      # doanh thu hóa đơn trong ngày, đã trừ trả hàng
    sales_invoices: int
```

(`date`, `Decimal`, `BaseModel` đã import sẵn.)

- [ ] **Step 2: service** — thêm vào `backend/modules/report/service.py`. Import `CashTransaction` và `ReturnOrder` đã có sẵn (Feature A/B); `timedelta` đã import. Thêm helper VN-day-range + hàm `end_of_day`:

```python
VN_TZ = timezone(timedelta(hours=7))
CASH_METHODS = ["CASH", "BANK_TRANSFER", "EWALLET"]


def _vn_day_range(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=VN_TZ)
    return start, start + timedelta(days=1)


async def end_of_day(db: AsyncSession, tenant_id: int, business_date: date) -> dict[str, Any]:
    start, end = _vn_day_range(business_date)

    # Lũy kế trước đầu ngày theo method (opening)
    open_rows = (await db.execute(
        select(
            CashTransaction.method,
            CashTransaction.direction,
            func.coalesce(func.sum(CashTransaction.amount), 0),
        ).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.status == "ACTIVE",
            CashTransaction.created_at < start,
        ).group_by(CashTransaction.method, CashTransaction.direction)
    )).all()
    opening: dict[str, Decimal] = {}
    for m, d, v in open_rows:
        delta = Decimal(str(v or 0)) * (Decimal("1") if d == "IN" else Decimal("-1"))
        opening[m] = opening.get(m, Decimal("0")) + delta

    # Thu/chi trong ngày theo method
    day_rows = (await db.execute(
        select(
            CashTransaction.method,
            CashTransaction.direction,
            func.coalesce(func.sum(CashTransaction.amount), 0),
        ).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.status == "ACTIVE",
            CashTransaction.created_at >= start,
            CashTransaction.created_at < end,
        ).group_by(CashTransaction.method, CashTransaction.direction)
    )).all()
    day_in: dict[str, Decimal] = {}
    day_out: dict[str, Decimal] = {}
    for m, d, v in day_rows:
        if d == "IN":
            day_in[m] = day_in.get(m, Decimal("0")) + Decimal(str(v or 0))
        else:
            day_out[m] = day_out.get(m, Decimal("0")) + Decimal(str(v or 0))

    methods = set(CASH_METHODS) | set(opening) | set(day_in) | set(day_out)
    by_method = []
    for m in sorted(methods):
        op = opening.get(m, Decimal("0"))
        i = day_in.get(m, Decimal("0"))
        o = day_out.get(m, Decimal("0"))
        by_method.append({
            "method": m, "opening": op, "total_in": i, "total_out": o,
            "closing": op + i - o,
        })

    opening_total = sum((r["opening"] for r in by_method), Decimal("0"))
    in_total = sum((r["total_in"] for r in by_method), Decimal("0"))
    out_total = sum((r["total_out"] for r in by_method), Decimal("0"))
    closing_total = opening_total + in_total - out_total

    # Doanh thu bán hàng trong ngày (hóa đơn COMPLETED) − trả hàng trong ngày
    sales_row = (await db.execute(
        select(
            func.coalesce(func.sum(Invoice.total), 0),
            func.count(Invoice.id),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.completed_at >= start,
            Invoice.completed_at < end,
        )
    )).one()
    gross_sales = Decimal(str(sales_row[0] or 0))
    sales_invoices = int(sales_row[1] or 0)
    ret_refund, _ret_cost, _ = await _returns_totals(db, tenant_id, start, end)
    sales_revenue = gross_sales - ret_refund

    return {
        "business_date": business_date,
        "by_method": by_method,
        "opening_total": opening_total,
        "in_total": in_total,
        "out_total": out_total,
        "closing_total": closing_total,
        "sales_revenue": sales_revenue,
        "sales_invoices": sales_invoices,
    }
```

> Lưu ý: `timezone` đã import (đầu file dùng `timezone.utc`). `_returns_totals` đã có (Feature A). Nếu `CASH_METHODS`/`VN_TZ` trùng tên đã định nghĩa nơi khác thì bỏ khai báo trùng.

- [ ] **Step 3: Router** — `backend/modules/report/router.py`: import `EndOfDayResponse, EodMethodRow` + endpoint:

```python
@router.get("/end-of-day", response_model=EndOfDayResponse)
async def end_of_day(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
    business_date: date | None = Query(default=None, alias="date"),
):
    from datetime import datetime, timedelta, timezone as _tz
    d = business_date or datetime.now(tz=_tz(timedelta(hours=7))).date()
    data = await report_service.end_of_day(db, owner.current_tenant_id, d)
    return EndOfDayResponse(
        business_date=data["business_date"],
        by_method=[EodMethodRow(**r) for r in data["by_method"]],
        opening_total=data["opening_total"],
        in_total=data["in_total"],
        out_total=data["out_total"],
        closing_total=data["closing_total"],
        sales_revenue=data["sales_revenue"],
        sales_invoices=data["sales_invoices"],
    )
```

- [ ] **Step 4: tests** — thêm vào `tests/test_report.py`:

```python
@pytest.mark.asyncio
async def test_end_of_day_cash_and_sales(client, shop):
    from datetime import datetime, timezone, timedelta
    h = shop["headers"]
    vn_today = datetime.now(tz=timezone(timedelta(hours=7))).date().isoformat()

    # bán 2 cái p1 (12000) tiền mặt → thu 24000, doanh thu 24000
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 24000}],
    }, headers=h)
    # chi tay tiền điện 5000
    await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "OPERATING", "amount": 5000,
    }, headers=h)

    r = await client.get(f"/api/v1/reports/end-of-day?date={vn_today}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["business_date"] == vn_today
    cash = next(m for m in body["by_method"] if m["method"] == "CASH")
    assert float(cash["total_in"]) == 24000
    assert float(cash["total_out"]) == 5000
    assert float(cash["closing"]) == float(cash["opening"]) + 24000 - 5000
    assert float(body["sales_revenue"]) == 24000
    assert body["sales_invoices"] == 1


@pytest.mark.asyncio
async def test_end_of_day_owner_only(client, shop, registered_owner):
    await client.post("/api/v1/staff", json={
        "full_name": "C", "phone": "0912777888", "password": "secret123",
    }, headers=shop["headers"])
    ct = (await client.post("/api/v1/auth/login", json={"phone": "0912777888", "password": "secret123"})).json()["access_token"]
    r = await client.get("/api/v1/reports/end-of-day", headers=_auth(ct))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_end_of_day_default_today(client, shop):
    r = await client.get("/api/v1/reports/end-of-day", headers=shop["headers"])
    assert r.status_code == 200
```

- [ ] **Step 5: Run** — `python -m pytest tests/test_report.py -q` → all pass. Sau đó full `python -m pytest tests/ -q`.
- [ ] **Step 6: Commit**

```bash
git add backend/modules/report/schemas.py backend/modules/report/service.py backend/modules/report/router.py tests/test_report.py
git commit -m "feat(eod): end-of-day report (VN timezone, per-method balance + sales)"
```

---

### Task 2: Frontend — API + MSW + page + nav

**Files:**
- Modify: `frontend/src/api/report.ts`, `frontend/src/__tests__/mocks/handlers.ts`, `frontend/src/App.tsx`, `frontend/src/components/AppLayout.tsx`
- Create: `frontend/src/pages/reports/EndOfDayPage.tsx` + `__tests__/EndOfDayPage.test.tsx`

- [ ] **Step 1: api/report.ts** — thêm:

```typescript
export interface EodMethodRow {
  method: string;
  opening: number | string;
  total_in: number | string;
  total_out: number | string;
  closing: number | string;
}
export interface EndOfDayResponse {
  business_date: string;
  by_method: EodMethodRow[];
  opening_total: number | string;
  in_total: number | string;
  out_total: number | string;
  closing_total: number | string;
  sales_revenue: number | string;
  sales_invoices: number;
}
export async function getEndOfDay(date?: string): Promise<EndOfDayResponse> {
  const { data } = await apiClient.get<EndOfDayResponse>('/reports/end-of-day', {
    params: date ? { date } : {},
  });
  return data;
}
```

- [ ] **Step 2: MSW** — thêm handler:

```typescript
  http.get('*/reports/end-of-day', ({ request }) => {
    const url = new URL(request.url);
    return HttpResponse.json({
      business_date: url.searchParams.get('date') ?? '2026-06-07',
      by_method: [
        { method: 'CASH', opening: 100000, total_in: 24000, total_out: 5000, closing: 119000 },
        { method: 'BANK_TRANSFER', opening: 0, total_in: 0, total_out: 0, closing: 0 },
        { method: 'EWALLET', opening: 0, total_in: 0, total_out: 0, closing: 0 },
      ],
      opening_total: 100000, in_total: 24000, out_total: 5000, closing_total: 119000,
      sales_revenue: 24000, sales_invoices: 1,
    });
  }),
```

- [ ] **Step 3: test (failing)** — `frontend/src/pages/reports/__tests__/EndOfDayPage.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import EndOfDayPage from '../EndOfDayPage';

describe('EndOfDayPage', () => {
  it('renders per-method balance + sales', async () => {
    render(<MemoryRouter><EndOfDayPage /></MemoryRouter>);
    expect(await screen.findByText('Báo cáo cuối ngày')).toBeInTheDocument();
    expect(await screen.findByText('Tiền mặt')).toBeInTheDocument();
    // tồn cuối tiền mặt 119.000
    expect(screen.getByText('119.000 VNĐ')).toBeInTheDocument();
    // doanh thu 24.000
    expect(screen.getAllByText('24.000 VNĐ').length).toBeGreaterThan(0);
  });
});
```

- [ ] **Step 4: Run → FAIL** — `cd frontend && npx vitest run src/pages/reports/__tests__/EndOfDayPage.test.tsx`.

- [ ] **Step 5: Tạo `EndOfDayPage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react';
import dayjs from 'dayjs';
import * as reportApi from '../../api/report';
import type { EndOfDayResponse } from '../../api/report';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import { SkeletonCard } from '../../components/Skeleton';

const METHOD_LABELS: Record<string, string> = {
  CASH: 'Tiền mặt', BANK_TRANSFER: 'Chuyển khoản', EWALLET: 'Ví điện tử',
};

export default function EndOfDayPage() {
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [data, setData] = useState<EndOfDayResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (d: string) => {
    setLoading(true); setError(null);
    try { setData(await reportApi.getEndOfDay(d)); }
    catch (e) { setError(toFriendlyMessage(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(date); /* eslint-disable-next-line */ }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Báo cáo cuối ngày</h1>
      <div className="flex items-end gap-3">
        <label className="text-sm">
          <span className="block text-slate-600 mb-1">Ngày</span>
          <input type="date" aria-label="Ngày" value={date}
            onChange={(e) => setDate(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1" />
        </label>
        <button onClick={() => load(date)} className="px-3 py-2 rounded bg-slate-900 text-white">Xem</button>
      </div>

      {error && <div role="alert" className="text-sm text-rose-600">{error}</div>}

      {loading ? <SkeletonCard /> : data && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white border border-slate-200 rounded p-4">
              <div className="text-sm text-slate-500">Doanh thu bán hàng</div>
              <div className="text-xl font-semibold">{formatVND(data.sales_revenue)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded p-4">
              <div className="text-sm text-slate-500">Số hóa đơn</div>
              <div className="text-xl font-semibold">{data.sales_invoices}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded p-4">
              <div className="text-sm text-slate-500">Tồn quỹ cuối ngày</div>
              <div className="text-xl font-semibold">{formatVND(data.closing_total)}</div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600"><tr>
                <th className="px-3 py-2 text-left">Phương thức</th>
                <th className="px-3 py-2 text-right">Tồn đầu ngày</th>
                <th className="px-3 py-2 text-right">Thu</th>
                <th className="px-3 py-2 text-right">Chi</th>
                <th className="px-3 py-2 text-right">Tồn cuối ngày</th>
              </tr></thead>
              <tbody>
                {data.by_method.map((m) => (
                  <tr key={m.method} className="border-t border-slate-100">
                    <td className="px-3 py-2">{METHOD_LABELS[m.method] ?? m.method}</td>
                    <td className="px-3 py-2 text-right">{formatVND(m.opening)}</td>
                    <td className="px-3 py-2 text-right text-emerald-700">{formatVND(m.total_in)}</td>
                    <td className="px-3 py-2 text-right text-rose-700">{formatVND(m.total_out)}</td>
                    <td className="px-3 py-2 text-right font-medium">{formatVND(m.closing)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50 font-semibold border-t-2 border-slate-300">
                <tr>
                  <td className="px-3 py-2">Tổng</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.opening_total)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.in_total)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.out_total)}</td>
                  <td className="px-3 py-2 text-right">{formatVND(data.closing_total)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Run → PASS** — `cd frontend && npx vitest run src/pages/reports/__tests__/EndOfDayPage.test.tsx`.

- [ ] **Step 7: Routes + nav (OWNER)** — App.tsx: `const EndOfDayPage = lazy(() => import('./pages/reports/EndOfDayPage'));` + route `/reports/end-of-day` bọc `OwnerOnly`. AppLayout.tsx: nav owner-only `{ to: '/reports/end-of-day', label: 'Cuối ngày', icon: icons.revenue }`.

- [ ] **Step 8: Verify + commit**

Run: `cd frontend && npx tsc --noEmit && npx vitest run` → all pass.

```bash
git add frontend/src/api/report.ts frontend/src/__tests__/mocks/handlers.ts frontend/src/pages/reports/EndOfDayPage.tsx frontend/src/pages/reports/__tests__/EndOfDayPage.test.tsx frontend/src/App.tsx frontend/src/components/AppLayout.tsx
git commit -m "feat(eod-fe): end-of-day report page, route+nav"
```

---

### Task 3: Verify toàn hệ thống

- [ ] **Step 1:** `python -m pytest tests/ -q` → all pass.
- [ ] **Step 2:** `cd frontend && npx tsc --noEmit && npx vitest run` → all pass.

---

## Self-Review

**Spec coverage:** tồn đầu/cuối ngày theo method (Task 1 `end_of_day`) ✅; tổng thu/chi (✅); doanh thu − trả hàng (✅ dùng `_returns_totals`); số HĐ (✅); **fix timezone VN** (`_vn_day_range` UTC+7) ✅; read-only, không bảng/migration ✅; OWNER-only (router) ✅; FE page + thẻ tổng + bảng per-method + nav (Task 2) ✅; tiếng Việt ✅.

**Migration checklist:** tenant_id mọi query ✅; read-only → không audit/migration; require_role OWNER ✅.

**Placeholder scan:** không. Code đầy đủ.

**Type consistency:** service dict khớp `EndOfDayResponse`/`EodMethodRow`. FE interface khớp. `VN_TZ`/`CASH_METHODS` khai báo 1 lần (kiểm tra trùng). Router default date dùng VN now.

**Lưu ý:** test phải tính `business_date` theo VN now (đã làm trong test) để tránh lệch ngày UTC↔VN. `_returns_totals` nhận (start,end) aware VN — nhất quán filter completed_at. Không "tiền thực đếm" (defer Kết ca).
