import pytest


def _auth(t): return {"Authorization": f"Bearer {t}"}


@pytest.fixture
async def shop(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "Coca", "sku": "COC", "sale_price": 12000, "cost_price": 9000,
    }, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 100, "cost_price": 9000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    return {"h": h, "p": p, "token": registered_owner["access_token"]}


async def _sell(client, h, pid, qty, paid=None):
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": pid, "quantity": qty}],
    }, headers=h)).json()
    amt = paid if paid is not None else float(inv["total"])
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": amt}],
    }, headers=h)
    return inv


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
