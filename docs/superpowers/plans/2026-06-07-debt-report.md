# Báo cáo công nợ KH/NCC (Derived) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Báo cáo công nợ **read-only derived**: KH nợ (phải thu) = Σ(hóa đơn chưa trả) − Σ(thu nợ); NCC nợ (phải trả) = Σ(phiếu nhập chưa trả) − Σ(trả nợ). Thêm 2 category cash book `DEBT_COLLECTION`/`DEBT_PAYMENT` (gắn đối tác) để ghi nhận thu/trả nợ sau. OWNER-only.

**Architecture:** KHÔNG bảng mới, KHÔNG migration. Suy số nợ từ `invoices`/`goods_receipts` (`total − paid_amount`, status COMPLETED) trừ các phiếu cash book thu/trả nợ (gắn `partner_id`). Tôn trọng quyết định defer "sổ công nợ riêng" trong CLAUDE.md.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, pytest (SQLite), React 18 + TS + Vitest + MSW.

**Quyết định (Gate 1):** derived + category thu/trả nợ; không ledger; OWNER-only.

**Giới hạn MVP (ghi rõ):** chỉ tính đối tác có `id` (bỏ KH vãng lai `customer_id=null` — không quy được); hóa đơn/phiếu CANCELLED tự loại (filter COMPLETED); **trả hàng KHÔNG tự giảm công nợ** (trả hàng hoàn tiền mặt, không coupling công nợ — edge bán-chịu-rồi-trả hiếm, defer); không có "điều chỉnh nợ"/"nợ đầu kỳ onboard".

---

### Task 1: Cashbook — 2 category thu/trả nợ + validate đối tác

**Files:**
- Modify: `backend/modules/cashbook/service.py`
- Modify: `backend/modules/cashbook/schemas.py`
- Test: `tests/test_cashbook.py` (thêm)

- [ ] **Step 1: service categories + validate** — trong `backend/modules/cashbook/service.py`:
  - Thêm `DEBT_COLLECTION` vào `VALID_IN_CATEGORIES`; `DEBT_PAYMENT` vào `VALID_OUT_CATEGORIES`:

```python
VALID_IN_CATEGORIES = {"SALE", "OTHER_IN", "CAPITAL", "DEBT_COLLECTION"}
VALID_OUT_CATEGORIES = {"PURCHASE", "CHANGE", "SALARY", "OPERATING", "OTHER_OUT", "REFUND", "DEBT_PAYMENT"}
```

(`AUTO_ONLY_CATEGORIES` giữ nguyên — DEBT_* được tạo TAY.)

  - Trong `create_cash_transaction`, sau khối validate category (trước `record_cash_entry`), thêm yêu cầu đối tác cho DEBT_*:

```python
    if cat in {"DEBT_COLLECTION", "DEBT_PAYMENT"}:
        if payload.partner_type is None or payload.partner_id is None:
            raise AppError(400, "DEBT_PARTNER_REQUIRED", "Thu/trả nợ phải chọn đối tác")
        expected = "CUSTOMER" if cat == "DEBT_COLLECTION" else "SUPPLIER"
        if payload.partner_type != expected:
            raise AppError(400, "DEBT_PARTNER_MISMATCH", "Đối tác không khớp loại thu/trả nợ")
```

- [ ] **Step 2: schemas** — `backend/modules/cashbook/schemas.py`, cập nhật Literal (không bắt buộc nhưng cho rõ):

```python
ManualInCategory = Literal["OTHER_IN", "CAPITAL", "DEBT_COLLECTION"]
ManualOutCategory = Literal["SALARY", "OPERATING", "OTHER_OUT", "DEBT_PAYMENT"]
```

- [ ] **Step 3: test** — thêm vào `tests/test_cashbook.py`:

```python
@pytest.mark.asyncio
async def test_debt_collection_requires_partner(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "DEBT_COLLECTION", "amount": 50000,
    }, headers=owner_h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "DEBT_PARTNER_REQUIRED"


@pytest.mark.asyncio
async def test_debt_collection_with_partner_ok(client, owner_h):
    cus = (await client.post("/api/v1/customers", json={"name": "A", "phone": "0905000123"}, headers=owner_h)).json()
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "DEBT_COLLECTION", "amount": 50000,
        "partner_type": "CUSTOMER", "partner_id": cus["id"],
    }, headers=owner_h)
    assert r.status_code == 201
```

- [ ] **Step 4: Run** — `python -m pytest tests/test_cashbook.py -q` → all pass.
- [ ] **Step 5: Commit**

```bash
git add backend/modules/cashbook/service.py backend/modules/cashbook/schemas.py tests/test_cashbook.py
git commit -m "feat(debt): DEBT_COLLECTION/DEBT_PAYMENT cash categories with partner"
```

---

### Task 2: Report — schemas + service (derived debt)

**Files:**
- Modify: `backend/modules/report/schemas.py`
- Modify: `backend/modules/report/service.py`
- Test: `tests/test_report.py` (thêm)

- [ ] **Step 1: schemas** — thêm vào `backend/modules/report/schemas.py`:

```python
class DebtItem(BaseModel):
    partner_id: int
    partner_name: str
    phone: str | None = None
    debt: Decimal


class DebtReportResponse(BaseModel):
    items: list[DebtItem]
    total_debt: Decimal
```

- [ ] **Step 2: service** — thêm import + 2 hàm vào `backend/modules/report/service.py`:

```python
from backend.modules.customer.models import Customer, Supplier
from backend.modules.inventory.models import GoodsReceipt
from backend.modules.cashbook.models import CashTransaction
```

(Customer có thể đã import; kiểm tra tránh trùng. Inventory đã import Inventory — thêm GoodsReceipt.)

```python
async def customer_debts(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    # Nợ phát sinh = Σ(total - paid) hóa đơn COMPLETED, customer_id not null
    owed_rows = (await db.execute(
        select(
            Invoice.customer_id,
            func.coalesce(func.sum(Invoice.total - Invoice.paid_amount), 0),
        ).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == "COMPLETED",
            Invoice.customer_id.isnot(None),
        ).group_by(Invoice.customer_id)
    )).all()
    owed = {cid: Decimal(str(v or 0)) for cid, v in owed_rows}

    # Đã thu nợ = Σ cash IN category=DEBT_COLLECTION ACTIVE, partner CUSTOMER
    coll_rows = (await db.execute(
        select(
            CashTransaction.partner_id,
            func.coalesce(func.sum(CashTransaction.amount), 0),
        ).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.status == "ACTIVE",
            CashTransaction.direction == "IN",
            CashTransaction.category == "DEBT_COLLECTION",
            CashTransaction.partner_type == "CUSTOMER",
            CashTransaction.partner_id.isnot(None),
        ).group_by(CashTransaction.partner_id)
    )).all()
    collected = {pid: Decimal(str(v or 0)) for pid, v in coll_rows}

    partner_ids = set(owed) | set(collected)
    debts: dict[int, Decimal] = {}
    for pid in partner_ids:
        d = owed.get(pid, Decimal("0")) - collected.get(pid, Decimal("0"))
        if d > 0:
            debts[pid] = d

    items = []
    if debts:
        crows = (await db.execute(
            select(Customer).where(Customer.tenant_id == tenant_id, Customer.id.in_(list(debts.keys())))
        )).scalars().all()
        cmap = {c.id: c for c in crows}
        for pid, d in sorted(debts.items(), key=lambda kv: kv[1], reverse=True):
            c = cmap.get(pid)
            items.append({
                "partner_id": pid,
                "partner_name": c.name if c else "Khách đã xóa",
                "phone": c.phone if c else None,
                "debt": d,
            })
    return {"items": items, "total_debt": sum((i["debt"] for i in items), Decimal("0"))}


async def supplier_debts(db: AsyncSession, tenant_id: int) -> dict[str, Any]:
    owed_rows = (await db.execute(
        select(
            GoodsReceipt.supplier_id,
            func.coalesce(func.sum(GoodsReceipt.total - GoodsReceipt.paid_amount), 0),
        ).where(
            GoodsReceipt.tenant_id == tenant_id,
            GoodsReceipt.status == "COMPLETED",
            GoodsReceipt.supplier_id.isnot(None),
        ).group_by(GoodsReceipt.supplier_id)
    )).all()
    owed = {sid: Decimal(str(v or 0)) for sid, v in owed_rows}

    paid_rows = (await db.execute(
        select(
            CashTransaction.partner_id,
            func.coalesce(func.sum(CashTransaction.amount), 0),
        ).where(
            CashTransaction.tenant_id == tenant_id,
            CashTransaction.status == "ACTIVE",
            CashTransaction.direction == "OUT",
            CashTransaction.category == "DEBT_PAYMENT",
            CashTransaction.partner_type == "SUPPLIER",
            CashTransaction.partner_id.isnot(None),
        ).group_by(CashTransaction.partner_id)
    )).all()
    paid = {pid: Decimal(str(v or 0)) for pid, v in paid_rows}

    partner_ids = set(owed) | set(paid)
    debts: dict[int, Decimal] = {}
    for pid in partner_ids:
        d = owed.get(pid, Decimal("0")) - paid.get(pid, Decimal("0"))
        if d > 0:
            debts[pid] = d

    items = []
    if debts:
        srows = (await db.execute(
            select(Supplier).where(Supplier.tenant_id == tenant_id, Supplier.id.in_(list(debts.keys())))
        )).scalars().all()
        smap = {s.id: s for s in srows}
        for pid, d in sorted(debts.items(), key=lambda kv: kv[1], reverse=True):
            s = smap.get(pid)
            items.append({
                "partner_id": pid,
                "partner_name": s.name if s else "NCC đã xóa",
                "phone": s.phone if s else None,
                "debt": d,
            })
    return {"items": items, "total_debt": sum((i["debt"] for i in items), Decimal("0"))}
```

- [ ] **Step 3: tests** — thêm vào `tests/test_report.py`:

```python
@pytest.mark.asyncio
async def test_customer_debt_derived(client, shop):
    h = shop["headers"]
    cus = (await client.post("/api/v1/customers", json={"name": "Nợ A", "phone": "0905111222"}, headers=h)).json()
    # bán chịu: total 24000, trả 10000 → nợ 14000
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": cus["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 10000}], "allow_debt": True,
    }, headers=h)

    r = await client.get("/api/v1/reports/debts/customers", headers=h)
    assert r.status_code == 200
    body = r.json()
    item = next(i for i in body["items"] if i["partner_id"] == cus["id"])
    assert float(item["debt"]) == 14000

    # thu nợ 4000 → còn 10000
    await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "DEBT_COLLECTION", "amount": 4000,
        "partner_type": "CUSTOMER", "partner_id": cus["id"],
    }, headers=h)
    r2 = await client.get("/api/v1/reports/debts/customers", headers=h)
    item2 = next(i for i in r2.json()["items"] if i["partner_id"] == cus["id"])
    assert float(item2["debt"]) == 10000


@pytest.mark.asyncio
async def test_customer_debt_owner_only(client, shop, registered_owner):
    await client.post("/api/v1/staff", json={
        "full_name": "C", "phone": "0912555666", "password": "secret123",
    }, headers=shop["headers"])
    ct = (await client.post("/api/v1/auth/login", json={"phone": "0912555666", "password": "secret123"})).json()["access_token"]
    r = await client.get("/api/v1/reports/debts/customers", headers=_auth(ct))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_supplier_debt_derived(client, shop):
    h = shop["headers"]
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC X"}, headers=h)).json()
    # nhập chịu: total 200000, trả 50000 → nợ 150000
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 20000}],
        "paid_amount": 50000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    rep = await client.get("/api/v1/reports/debts/suppliers", headers=h)
    item = next(i for i in rep.json()["items"] if i["partner_id"] == sup["id"])
    assert float(item["debt"]) == 150000
```

> Lưu ý: `shop` fixture trong test_report.py có p1 (sale 12000). Kiểm tra goods-receipt schema có nhận `supplier_id` + `paid_amount` (đọc inventory schema nếu cần). `allow_debt` là field của complete payload (xem complete_invoice). Nếu tên khác, đọc schema sales để chỉnh.

- [ ] **Step 4: Router** — `backend/modules/report/router.py`: import `DebtReportResponse, DebtItem` + thêm 2 endpoint (cạnh các report khác):

```python
@router.get("/debts/customers", response_model=DebtReportResponse)
async def customer_debts(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    data = await report_service.customer_debts(db, owner.current_tenant_id)
    return DebtReportResponse(items=[DebtItem(**i) for i in data["items"]], total_debt=data["total_debt"])


@router.get("/debts/suppliers", response_model=DebtReportResponse)
async def supplier_debts(
    db: Annotated[AsyncSession, Depends(get_db)],
    owner: Annotated[User, Depends(require_role("OWNER"))],
):
    data = await report_service.supplier_debts(db, owner.current_tenant_id)
    return DebtReportResponse(items=[DebtItem(**i) for i in data["items"]], total_debt=data["total_debt"])
```

- [ ] **Step 5: Run** — `python -m pytest tests/test_report.py -q` → all pass.
- [ ] **Step 6: Commit**

```bash
git add backend/modules/report/schemas.py backend/modules/report/service.py backend/modules/report/router.py tests/test_report.py
git commit -m "feat(debt): derived customer/supplier debt report endpoints"
```

---

### Task 3: Frontend — API + cashbook partner + MSW

**Files:**
- Modify: `frontend/src/api/report.ts`
- Modify: `frontend/src/api/cashbook.ts` (cho phép partner trong payload)
- Modify: `frontend/src/__tests__/mocks/handlers.ts`

- [ ] **Step 1: report.ts** — thêm types + 2 hàm:

```typescript
export interface DebtItem {
  partner_id: number;
  partner_name: string;
  phone: string | null;
  debt: number | string;
}
export interface DebtReportResponse {
  items: DebtItem[];
  total_debt: number | string;
}
export async function getCustomerDebts(): Promise<DebtReportResponse> {
  const { data } = await apiClient.get<DebtReportResponse>('/reports/debts/customers');
  return data;
}
export async function getSupplierDebts(): Promise<DebtReportResponse> {
  const { data } = await apiClient.get<DebtReportResponse>('/reports/debts/suppliers');
  return data;
}
```

- [ ] **Step 2: cashbook.ts** — mở rộng `CashCreatePayload` để gắn đối tác (cho thu/trả nợ):

```typescript
export interface CashCreatePayload {
  direction: CashDirection;
  method: CashMethod;
  category: string;
  amount: number;
  partner_type?: 'CUSTOMER' | 'SUPPLIER' | 'OTHER';
  partner_id?: number;
  partner_name?: string;
  note?: string;
}
```

(Hàm `createCash` giữ nguyên — chỉ payload mở rộng.)

- [ ] **Step 3: MSW** — thêm handlers:

```typescript
  http.get('*/reports/debts/customers', () =>
    HttpResponse.json({
      items: [{ partner_id: 1, partner_name: 'Nguyễn Văn A', phone: '0905111222', debt: 14000 }],
      total_debt: 14000,
    }),
  ),
  http.get('*/reports/debts/suppliers', () =>
    HttpResponse.json({
      items: [{ partner_id: 2, partner_name: 'NCC X', phone: null, debt: 150000 }],
      total_debt: 150000,
    }),
  ),
```

(Handler `*/cash-transactions` POST đã có — tái dùng cho thu/trả nợ.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/report.ts frontend/src/api/cashbook.ts frontend/src/__tests__/mocks/handlers.ts
git commit -m "feat(debt-fe): debt report api + cashbook partner payload + msw"
```

---

### Task 4: Frontend — trang Báo cáo công nợ + ghi thu/trả nợ

**Files:**
- Create: `frontend/src/pages/reports/DebtReportPage.tsx` + `__tests__/DebtReportPage.test.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/AppLayout.tsx`

- [ ] **Step 1: test (failing)** — `frontend/src/pages/reports/__tests__/DebtReportPage.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DebtReportPage from '../DebtReportPage';

describe('DebtReportPage', () => {
  it('renders customer + supplier debts', async () => {
    render(<MemoryRouter><DebtReportPage /></MemoryRouter>);
    expect(await screen.findByText('Báo cáo công nợ')).toBeInTheDocument();
    expect(await screen.findByText('Nguyễn Văn A')).toBeInTheDocument();
    expect(screen.getByText('NCC X')).toBeInTheDocument();
    expect(screen.getByText('14.000 VNĐ')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run → FAIL** — `cd frontend && npx vitest run src/pages/reports/__tests__/DebtReportPage.test.tsx`.

- [ ] **Step 3: Tạo `DebtReportPage.tsx`** — 2 bảng (KH phải thu / NCC phải trả), mỗi dòng có nút "Thu nợ"/"Trả nợ" mở input số tiền → gọi `cashApi.createCash` với category + partner tương ứng, rồi reload:

```tsx
import { useCallback, useEffect, useState } from 'react';
import * as reportApi from '../../api/report';
import type { DebtItem } from '../../api/report';
import * as cashApi from '../../api/cashbook';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';

type Kind = 'CUSTOMER' | 'SUPPLIER';

function DebtTable({
  title, kind, items, onPaid,
}: { title: string; kind: Kind; items: DebtItem[]; onPaid: () => void }) {
  const [payingId, setPayingId] = useState<number | null>(null);
  const [amount, setAmount] = useState('');
  const [err, setErr] = useState<string | null>(null);

  const submit = async (partner: DebtItem) => {
    const amt = Number(amount);
    if (!Number.isFinite(amt) || amt <= 0) { setErr('Số tiền phải lớn hơn 0'); return; }
    setErr(null);
    try {
      await cashApi.createCash({
        direction: kind === 'CUSTOMER' ? 'IN' : 'OUT',
        method: 'CASH',
        category: kind === 'CUSTOMER' ? 'DEBT_COLLECTION' : 'DEBT_PAYMENT',
        amount: amt,
        partner_type: kind,
        partner_id: partner.partner_id,
        partner_name: partner.partner_name,
      });
      setPayingId(null); setAmount('');
      onPaid();
    } catch (e) { setErr(toFriendlyMessage(e)); }
  };

  const label = kind === 'CUSTOMER' ? 'Thu nợ' : 'Trả nợ';
  return (
    <div className="space-y-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="bg-white border border-slate-200 rounded overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600"><tr>
            <th className="px-3 py-2 text-left">Đối tác</th>
            <th className="px-3 py-2 text-left">SĐT</th>
            <th className="px-3 py-2 text-right">Còn nợ</th>
            <th className="px-3 py-2"></th>
          </tr></thead>
          <tbody>
            {items.length === 0 ? (
              <tr><td colSpan={4} className="px-3 py-6"><EmptyState title="Không có công nợ" /></td></tr>
            ) : items.map((it) => (
              <tr key={it.partner_id} className="border-t border-slate-100">
                <td className="px-3 py-2">{it.partner_name}</td>
                <td className="px-3 py-2">{it.phone ?? ''}</td>
                <td className="px-3 py-2 text-right font-medium">{formatVND(it.debt)}</td>
                <td className="px-3 py-2 text-right">
                  {payingId === it.partner_id ? (
                    <span className="inline-flex items-center gap-1">
                      <input type="number" min="1" value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        aria-label={`Số tiền ${label}`}
                        className="w-28 px-2 py-1 border border-slate-300 rounded text-right" />
                      <button onClick={() => submit(it)} className="px-2 py-1 rounded bg-slate-900 text-white text-xs">Lưu</button>
                      <button onClick={() => { setPayingId(null); setErr(null); }} className="px-2 py-1 rounded border text-xs">Hủy</button>
                    </span>
                  ) : (
                    <button onClick={() => { setPayingId(it.partner_id); setAmount(''); }}
                      className="px-2 py-1 rounded border border-slate-300 text-xs">{label}</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {err && <div role="alert" className="text-sm text-rose-600">{err}</div>}
    </div>
  );
}

export default function DebtReportPage() {
  const [cus, setCus] = useState<DebtItem[]>([]);
  const [sup, setSup] = useState<DebtItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [c, s] = await Promise.all([reportApi.getCustomerDebts(), reportApi.getSupplierDebts()]);
      setCus(c.items); setSup(s.items);
    } catch (e) { setError(toFriendlyMessage(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Báo cáo công nợ</h1>
      {error && <div role="alert" className="text-sm text-rose-600">{error}</div>}
      {loading ? <SkeletonCard /> : (
        <>
          <DebtTable title="Khách hàng còn nợ (phải thu)" kind="CUSTOMER" items={cus} onPaid={load} />
          <DebtTable title="Nợ nhà cung cấp (phải trả)" kind="SUPPLIER" items={sup} onPaid={load} />
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run → PASS** — `cd frontend && npx vitest run src/pages/reports/__tests__/DebtReportPage.test.tsx`.

- [ ] **Step 5: Routes + nav (OWNER)** — App.tsx: `const DebtReportPage = lazy(() => import('./pages/reports/DebtReportPage'));` + route `/reports/debts` bọc `OwnerOnly`. AppLayout.tsx: thêm nav owner-only `{ to: '/reports/debts', label: 'Công nợ', icon: icons.customer }`.

- [ ] **Step 6: Verify + commit**

Run: `cd frontend && npx tsc --noEmit && npx vitest run` → all pass.

```bash
git add frontend/src/pages/reports/DebtReportPage.tsx frontend/src/pages/reports/__tests__/DebtReportPage.test.tsx frontend/src/App.tsx frontend/src/components/AppLayout.tsx
git commit -m "feat(debt-fe): debt report page with thu/trả nợ recording, route+nav"
```

---

### Task 5: Verify toàn hệ thống

- [ ] **Step 1:** `python -m pytest tests/ -q` → all pass.
- [ ] **Step 2:** `cd frontend && npx tsc --noEmit && npx vitest run` → all pass.

---

## Self-Review

**Spec coverage:** nợ KH derived (Task 2 `customer_debts`) ✅; nợ NCC derived (`supplier_debts`) ✅; thu/trả nợ qua cash category gắn đối tác (Task 1) → trừ vào report ✅ (test `test_customer_debt_derived` kiểm cả trước & sau thu nợ); OWNER-only (Task 2 router) ✅; FE 2 bảng + ghi thu/trả nợ (Task 4) ✅; nav+route ✅; tiếng Việt ✅. KHÔNG migration/bảng mới ✅ (đúng defer CLAUDE.md).

**Migration checklist:** tenant_id mọi query ✅; read-only → không audit/migration; DEBT_* tạo tay có ghi audit qua `create_cash_transaction` (CREATE_CASH_TX) ✅; require_role OWNER ✅.

**Placeholder scan:** không. Code đầy đủ; Task 2/4 wiring mô tả vị trí + code.

**Type consistency:** service trả dict {items, total_debt} → `DebtReportResponse`/`DebtItem`. FE DebtItem khớp. cashbook createCash payload mở rộng partner — backend `CashTransactionCreate` đã có sẵn partner fields.

**Giới hạn đã ghi (MVP):** bỏ KH vãng lai; trả hàng không giảm công nợ; không điều chỉnh/nợ đầu kỳ. Import: report.service import customer/inventory/cashbook models (models only, không vòng).
