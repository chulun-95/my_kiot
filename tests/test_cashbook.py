import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def owner_h(registered_owner):
    return _auth(registered_owner["access_token"])


@pytest.mark.asyncio
async def test_create_manual_receipt_and_balance(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "CAPITAL",
        "amount": 500000, "note": "Góp vốn",
    }, headers=owner_h)
    assert r.status_code == 201
    body = r.json()
    assert body["code"].startswith("PT")
    assert body["direction"] == "IN"
    assert body["ref_type"] == "MANUAL"

    lst = await client.get("/api/v1/cash-transactions", headers=owner_h)
    assert lst.status_code == 200
    data = lst.json()
    assert float(data["summary"]["balance_total"]) == 500000
    assert float(data["summary"]["range_in"]) == 500000
    by_cash = next(m for m in data["summary"]["balance_by_method"] if m["method"] == "CASH")
    assert float(by_cash["balance"]) == 500000


@pytest.mark.asyncio
async def test_create_manual_payment_code_pc(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "SALARY", "amount": 200000,
    }, headers=owner_h)
    assert r.status_code == 201
    assert r.json()["code"].startswith("PC")


@pytest.mark.asyncio
async def test_manual_rejects_auto_only_category(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "SALE", "amount": 1000,
    }, headers=owner_h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_CASH_CATEGORY"


@pytest.mark.asyncio
async def test_cancel_manual_excluded_from_balance(client, owner_h):
    created = (await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "OTHER_IN", "amount": 300000,
    }, headers=owner_h)).json()
    c = await client.post(
        f"/api/v1/cash-transactions/{created['id']}/cancel",
        json={"reason": "nhầm"}, headers=owner_h,
    )
    assert c.status_code == 200
    assert c.json()["status"] == "CANCELLED"

    data = (await client.get("/api/v1/cash-transactions", headers=owner_h)).json()
    assert float(data["summary"]["balance_total"]) == 0


@pytest.mark.asyncio
async def test_cashbook_owner_only(client, registered_owner):
    await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0912000111", "password": "secret123",
    }, headers=_auth(registered_owner["access_token"]))
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0912000111", "password": "secret123",
    })).json()["access_token"]
    r = await client.get("/api/v1/cash-transactions", headers=_auth(cashier_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cashbook_filter_by_direction(client, owner_h):
    await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "OTHER_IN", "amount": 100000,
    }, headers=owner_h)
    await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "OTHER_OUT", "amount": 40000,
    }, headers=owner_h)
    data = (await client.get(
        "/api/v1/cash-transactions?direction=OUT", headers=owner_h
    )).json()
    assert all(i["direction"] == "OUT" for i in data["items"])
    assert float(data["summary"]["balance_total"]) == 60000  # summary luôn tính toàn bộ


async def _stock_product(client, h, sku, sale, cost, qty):
    p = (await client.post("/api/v1/products", json={
        "name": sku, "sku": sku, "sale_price": sale, "cost_price": cost,
    }, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": qty, "cost_price": cost}],
        "paid_amount": 0,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    return p


@pytest.mark.asyncio
async def test_complete_invoice_creates_cash_in(client, owner_h):
    p = await _stock_product(client, owner_h, "AAA", 12000, 9000, 100)
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": p["id"], "quantity": 2}],
    }, headers=owner_h)).json()  # total 24000
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 50000}],  # thừa → thối 26000
    }, headers=owner_h)

    data = (await client.get("/api/v1/cash-transactions?ref_type=INVOICE", headers=owner_h)).json()
    cats = {i["category"]: float(i["amount"]) for i in data["items"]}
    assert cats["SALE"] == 50000      # phiếu thu = tiền nhận
    assert cats["CHANGE"] == 26000    # phiếu chi tiền thối
    # tồn quỹ tiền mặt = 50000 - 26000 = 24000 (đúng giá trị hóa đơn)
    assert float(data["summary"]["balance_total"]) == 24000


@pytest.mark.asyncio
async def test_cancel_invoice_reverses_cash(client, owner_h):
    p = await _stock_product(client, owner_h, "BBB", 10000, 6000, 100)
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": p["id"], "quantity": 1}],
    }, headers=owner_h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 10000}],
    }, headers=owner_h)
    await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "x"}, headers=owner_h)

    data = (await client.get("/api/v1/cash-transactions", headers=owner_h)).json()
    assert float(data["summary"]["balance_total"]) == 0  # phiếu thu auto đã CANCELLED


@pytest.mark.asyncio
async def test_complete_receipt_creates_cash_out(client, owner_h):
    p = (await client.post("/api/v1/products", json={
        "name": "CCC", "sku": "CCC", "sale_price": 5000, "cost_price": 3000,
    }, headers=owner_h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 10, "cost_price": 3000}],
        "paid_amount": 30000,
    }, headers=owner_h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=owner_h)

    data = (await client.get("/api/v1/cash-transactions?ref_type=GOODS_RECEIPT", headers=owner_h)).json()
    assert len(data["items"]) == 1
    assert data["items"][0]["category"] == "PURCHASE"
    assert float(data["items"][0]["amount"]) == 30000
    assert float(data["summary"]["balance_total"]) == -30000  # cho âm quỹ


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


@pytest.mark.asyncio
async def test_debt_payment_requires_partner(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "DEBT_PAYMENT", "amount": 100000,
    }, headers=owner_h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "DEBT_PARTNER_REQUIRED"


@pytest.mark.asyncio
async def test_debt_payment_with_partner_ok(client, owner_h):
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC X"}, headers=owner_h)).json()
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "DEBT_PAYMENT", "amount": 100000,
        "partner_type": "SUPPLIER", "partner_id": sup["id"],
    }, headers=owner_h)
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_debt_collection_partner_mismatch(client, owner_h):
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC Y"}, headers=owner_h)).json()
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "DEBT_COLLECTION", "amount": 50000,
        "partner_type": "SUPPLIER", "partner_id": sup["id"],
    }, headers=owner_h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "DEBT_PARTNER_MISMATCH"


@pytest.mark.asyncio
async def test_debt_payment_partner_mismatch(client, owner_h):
    cus = (await client.post("/api/v1/customers", json={"name": "B", "phone": "0905000456"}, headers=owner_h)).json()
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "DEBT_PAYMENT", "amount": 50000,
        "partner_type": "CUSTOMER", "partner_id": cus["id"],
    }, headers=owner_h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "DEBT_PARTNER_MISMATCH"
