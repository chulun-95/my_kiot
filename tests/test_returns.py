import pytest


def _auth(t): return {"Authorization": f"Bearer {t}"}


@pytest.fixture
async def shop(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "Coca", "sku": "COC", "sale_price": 12000, "cost_price": 9000,
    }, headers=h)).json()
    sup = (await client.post("/api/v1/suppliers", json={
        "name": "NCC Test",
    }, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [{"product_id": p["id"], "quantity": 100, "cost_price": 9000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    return {"h": h, "p": p, "supplier": sup, "token": registered_owner["access_token"]}


async def _sell(client, h, pid, qty, paid=None):
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": pid, "quantity": qty}],
    }, headers=h)).json()
    amt = paid if paid is not None else float(inv["total"])
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": amt}],
    }, headers=h)
    return inv


async def _sell_debt(client, h, pid, qty, customer_id, paid):
    """Bán nợ (paid < total) cho 1 khách cụ thể."""
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": customer_id,
        "items": [{"product_id": pid, "quantity": qty}],
    }, headers=h)).json()
    payments = [{"method": "CASH", "amount": paid}] if paid > 0 else []
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": payments, "allow_debt": True,
    }, headers=h)
    return inv


async def _make_customer(client, h, name="Khach No", phone="0912000111"):
    return (await client.post("/api/v1/customers", json={"name": name, "phone": phone}, headers=h)).json()


async def _customer_debt(client, h, customer_id):
    data = (await client.get("/api/v1/reports/debts/customers", headers=h)).json()
    for i in data["items"]:
        if i["partner_id"] == customer_id:
            return float(i["debt"])
    return 0.0


@pytest.mark.asyncio
async def test_returnable_lists_invoice_lines(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)
    r = await client.get(f"/api/v1/returns/returnable/{inv['id']}", headers=h)
    assert r.status_code == 200
    line = r.json()["lines"][0]
    assert float(line["sold_quantity"]) == 5
    assert float(line["returnable_quantity"]) == 5


@pytest.mark.asyncio
async def test_partial_return_restocks_and_refunds(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)  # total 60000
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]

    r = await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"],
        "items": [{"invoice_item_id": item_id, "quantity": 2}],
        "refund_method": "CASH",
    }, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["code"].startswith("TH")
    assert float(body["total_refund"]) == 24000  # 2 × 12000

    # tồn cộng lại: bán 5 còn 95 → trả 2 → 97
    inv_list = (await client.get("/api/v1/inventory", headers=h)).json()
    qty = next(i["quantity"] for i in inv_list["items"] if i["product_id"] == shop["p"]["id"])
    assert float(qty) == 97

    # cash book có phiếu chi REFUND
    cash = (await client.get("/api/v1/cash-transactions?ref_type=SALES_RETURN", headers=h)).json()
    assert any(i["category"] == "REFUND" and float(i["amount"]) == 24000 for i in cash["items"])


@pytest.mark.asyncio
async def test_cannot_return_more_than_bought(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 3)
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    # trả 2 lần: 2 + 2 = 4 > 3 → lần 2 lỗi
    await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)
    r2 = await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "RETURN_EXCEEDS_SOLD"


@pytest.mark.asyncio
async def test_return_reduces_revenue_report(client, shop):
    from datetime import date
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)  # revenue 60000
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)  # refund 24000
    today = date.today().isoformat()
    rev = (await client.get(f"/api/v1/reports/revenue?from={today}&to={today}", headers=h)).json()
    assert float(rev["total_revenue"]) == 60000 - 24000  # 36000


@pytest.mark.asyncio
async def test_cancel_return_owner_only(client, shop, registered_owner):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 2)
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    ret = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 1}],
    }, headers=h)).json()
    # cashier không hủy được
    s = await client.post("/api/v1/staff", json={
        "full_name": "Cashier Test", "phone": "0911333444", "password": "secret123",
    }, headers=h)
    assert s.status_code == 201, s.json()
    login_resp = await client.post("/api/v1/auth/login", json={"phone": "0911333444", "password": "secret123"})
    assert login_resp.status_code == 200
    ct = login_resp.json()["access_token"]
    rc = await client.post(f"/api/v1/returns/{ret['id']}/cancel", json={"reason": "x"}, headers=_auth(ct))
    assert rc.status_code == 403
    # owner hủy được → tồn trừ lại
    ro = await client.post(f"/api/v1/returns/{ret['id']}/cancel", json={"reason": "x"}, headers=h)
    assert ro.status_code == 200
    assert ro.json()["status"] == "CANCELLED"


# ====================================================================
# Lỗi #1 — chặn hủy hóa đơn đã có phiếu trả hàng ACTIVE
# ====================================================================

@pytest.mark.asyncio
async def test_cannot_cancel_invoice_with_active_return(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    ret = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)).json()

    # còn phiếu trả ACTIVE → không hủy được hóa đơn
    rc = await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "test"}, headers=h)
    assert rc.status_code == 400
    assert rc.json()["error"]["code"] == "INVOICE_HAS_RETURNS"
    assert ret["code"] in rc.json()["error"]["details"]["return_codes"]


@pytest.mark.asyncio
async def test_cancel_invoice_after_returns_cancelled_no_double_restock(client, shop):
    h = shop["h"]
    inv = await _sell(client, h, shop["p"]["id"], 5)  # 100 → 95
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    ret = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)).json()  # 95 → 97

    # hủy phiếu trả trước → 97 → 95
    await client.post(f"/api/v1/returns/{ret['id']}/cancel", json={"reason": "x"}, headers=h)
    # giờ hủy hóa đơn được → cộng lại đúng 5 (không cộng đôi) → 100
    rc = await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "x"}, headers=h)
    assert rc.status_code == 200

    inv_list = (await client.get("/api/v1/inventory", headers=h)).json()
    qty = next(i["quantity"] for i in inv_list["items"] if i["product_id"] == shop["p"]["id"])
    assert float(qty) == 100


# ====================================================================
# Lỗi #2 — trả hàng đơn nợ cấn trừ công nợ (kiểu KiotViet)
# ====================================================================

@pytest.mark.asyncio
async def test_return_full_debt_offset_no_cash(client, shop):
    h = shop["h"]
    cust = await _make_customer(client, h)
    inv = await _sell_debt(client, h, shop["p"]["id"], 5, cust["id"], paid=0)  # nợ 60000
    assert await _customer_debt(client, h, cust["id"]) == 60000

    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    r = await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert float(body["total_refund"]) == 24000
    assert float(body["debt_adjust"]) == 24000   # cấn hết vào nợ
    assert float(body["cash_refund"]) == 0

    # không có phiếu chi tiền mặt REFUND
    cash = (await client.get("/api/v1/cash-transactions?ref_type=SALES_RETURN", headers=h)).json()
    assert not any(i["category"] == "REFUND" for i in cash["items"])

    # nợ giảm còn 36000
    assert await _customer_debt(client, h, cust["id"]) == 36000


@pytest.mark.asyncio
async def test_return_partial_debt_offset_and_cash(client, shop):
    h = shop["h"]
    cust = await _make_customer(client, h, phone="0912000222")
    inv = await _sell_debt(client, h, shop["p"]["id"], 5, cust["id"], paid=50000)  # nợ 10000
    assert await _customer_debt(client, h, cust["id"]) == 10000

    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    body = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)).json()  # refund 24000
    assert float(body["debt_adjust"]) == 10000   # cấn hết nợ còn lại
    assert float(body["cash_refund"]) == 14000   # phần dư chi tiền

    cash = (await client.get("/api/v1/cash-transactions?ref_type=SALES_RETURN", headers=h)).json()
    assert any(i["category"] == "REFUND" and float(i["amount"]) == 14000 for i in cash["items"])

    # nợ về 0
    assert await _customer_debt(client, h, cust["id"]) == 0


@pytest.mark.asyncio
async def test_return_fully_paid_invoice_refunds_cash(client, shop):
    """Không hồi quy: đơn trả đủ tiền → cấn nợ = 0, hoàn 100% tiền mặt."""
    h = shop["h"]
    cust = await _make_customer(client, h, phone="0912000333")
    # bán có khách nhưng trả đủ tiền
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": cust["id"], "items": [{"product_id": shop["p"]["id"], "quantity": 5}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 60000}],
    }, headers=h)

    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    body = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)).json()
    assert float(body["debt_adjust"]) == 0
    assert float(body["cash_refund"]) == 24000


@pytest.mark.asyncio
async def test_cancel_return_restores_debt(client, shop):
    h = shop["h"]
    cust = await _make_customer(client, h, phone="0912000444")
    inv = await _sell_debt(client, h, shop["p"]["id"], 5, cust["id"], paid=0)  # nợ 60000
    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    ret = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)).json()
    assert await _customer_debt(client, h, cust["id"]) == 36000  # đã cấn 24000

    # hủy phiếu trả → nợ phục hồi về 60000
    await client.post(f"/api/v1/returns/{ret['id']}/cancel", json={"reason": "x"}, headers=h)
    assert await _customer_debt(client, h, cust["id"]) == 60000


# ====================================================================
# Lỗi #3 — trả hàng phân bổ chiết khấu toàn hóa đơn (không hoàn dư)
# ====================================================================

@pytest.mark.asyncio
async def test_return_allocates_order_discount(client, shop):
    h = shop["h"]
    # đơn: 5 × 12000 = 60000, CK tổng 6000 → total 54000, ratio 0.9
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p"]["id"], "quantity": 5}],
        "discount_amount": 6000,
    }, headers=h)).json()
    assert float(inv["total"]) == 54000
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 54000}],
    }, headers=h)

    item_id = (await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)).json()["items"][0]["id"]
    body = (await client.post("/api/v1/returns", json={
        "invoice_id": inv["id"], "items": [{"invoice_item_id": item_id, "quantity": 2}],
    }, headers=h)).json()
    # 2 × 12000 × 0.9 = 21600 (không phải 24000)
    assert float(body["total_refund"]) == 21600
    assert float(body["cash_refund"]) == 21600
