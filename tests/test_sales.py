import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- fixtures ----------

@pytest.fixture
async def shop(client, registered_owner):
    """Owner + 2 sản phẩm (đã nhập kho có tồn) + 1 khách hàng."""
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={
        "name": "Coca 330ml", "sku": "COC-330",
        "sale_price": 12000, "cost_price": 9000,
    }, headers=h)).json()
    p2 = (await client.post("/api/v1/products", json={
        "name": "Pepsi 1.5L", "sku": "PEP-1500",
        "sale_price": 25000, "cost_price": 20000,
    }, headers=h)).json()
    # Nhập kho để có tồn (gắn NCC, chưa trả tiền → không phát sinh dòng tiền)
    sup = (await client.post("/api/v1/suppliers", json={
        "name": "NCC Test",
    }, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [
            {"product_id": p1["id"], "quantity": 100, "cost_price": 9000},
            {"product_id": p2["id"], "quantity": 50, "cost_price": 20000},
        ],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    cust = (await client.post("/api/v1/customers", json={
        "name": "Nguyễn Văn A", "phone": "0987654321",
    }, headers=h)).json()
    return {
        "headers": h,
        "p1": p1,
        "p2": p2,
        "supplier": sup,
        "customer": cust,
        "token": registered_owner["access_token"],
        "user_id": registered_owner["user"]["id"],
        "tenant_id": registered_owner["tenant"]["id"],
    }


# ===================================================================
# CREATE
# ===================================================================

@pytest.mark.asyncio
async def test_create_invoice_minimal(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/invoices", json={
        "items": [
            {"product_id": shop["p1"]["id"], "quantity": 2},
        ],
    }, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"].startswith("HD")
    assert body["status"] == "DRAFT"
    assert float(body["subtotal"]) == 2 * 12000
    assert float(body["total"]) == 24000
    assert body["customer_id"] is None
    assert len(body["items"]) == 1
    assert body["items"][0]["product_name"] == "Coca 330ml"


@pytest.mark.asyncio
async def test_create_invoice_with_customer_and_discount(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/invoices", json={
        "customer_id": shop["customer"]["id"],
        "items": [
            {"product_id": shop["p1"]["id"], "quantity": 3},
            {"product_id": shop["p2"]["id"], "quantity": 1, "discount_amount": 5000},
        ],
        "discount_amount": 2000,
    }, headers=h)
    assert r.status_code == 201
    body = r.json()
    expected_sub = 3 * 12000 + (1 * 25000 - 5000)
    assert float(body["subtotal"]) == expected_sub
    assert float(body["total"]) == expected_sub - 2000
    assert body["customer_id"] == shop["customer"]["id"]
    assert body["customer_name"] == "Nguyễn Văn A"


@pytest.mark.asyncio
async def test_create_invoice_override_unit_price(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/invoices", json={
        "items": [
            {"product_id": shop["p1"]["id"], "quantity": 1, "unit_price": 10000},
        ],
    }, headers=h)
    body = r.json()
    assert float(body["items"][0]["unit_price"]) == 10000
    assert float(body["total"]) == 10000


@pytest.mark.asyncio
async def test_create_invoice_invalid_product(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/invoices", json={
        "items": [{"product_id": 99999, "quantity": 1}],
    }, headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_invoice_invalid_customer(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/invoices", json={
        "customer_id": 99999,
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_invoice_zero_quantity_rejected(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 0}],
    }, headers=h)
    assert r.status_code == 422


# ===================================================================
# UPDATE DRAFT
# ===================================================================

@pytest.mark.asyncio
async def test_update_draft_invoice(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()

    r = await client.put(f"/api/v1/invoices/{inv['id']}", json={
        "items": [
            {"product_id": shop["p1"]["id"], "quantity": 5},
            {"product_id": shop["p2"]["id"], "quantity": 2},
        ],
        "discount_amount": 1000,
    }, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    expected = 5 * 12000 + 2 * 25000 - 1000
    assert float(body["total"]) == expected


# ===================================================================
# COMPLETE
# ===================================================================

@pytest.mark.asyncio
async def test_complete_invoice_deducts_stock(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 3}],
    }, headers=h)).json()
    total = float(inv["total"])

    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": total}],
    }, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert body["completed_at"] is not None
    assert float(body["paid_amount"]) == total
    assert float(body["change_amount"]) == 0
    assert float(body["cost_total"]) == 3 * 9000

    # Check inventory decreased: 100 - 3 = 97
    inv_list = (await client.get("/api/v1/inventory", headers=h)).json()
    p1_row = next(i for i in inv_list["items"] if i["product_id"] == shop["p1"]["id"])
    assert float(p1_row["quantity"]) == 97


@pytest.mark.asyncio
async def test_complete_invoice_insufficient_payment_rejected(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 5}],
    }, headers=h)).json()

    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 1000}],
    }, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INSUFFICIENT_PAYMENT"


@pytest.mark.asyncio
async def test_complete_invoice_allow_debt(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": shop["customer"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 5}],
    }, headers=h)).json()

    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 10000}],
        "allow_debt": True,
    }, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert float(body["paid_amount"]) == 10000
    assert float(body["change_amount"]) == 0


@pytest.mark.asyncio
async def test_complete_invoice_debt_without_customer_rejected(client, shop):
    """Bán nợ (trả thiếu) cho khách vãng lai phải bị chặn — nợ sẽ không thống kê được."""
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 5}],
    }, headers=h)).json()

    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 10000}],
        "allow_debt": True,
    }, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "DEBT_REQUIRES_CUSTOMER"


@pytest.mark.asyncio
async def test_complete_invoice_change_amount(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()
    # Total = 12000, paid 20000 → thối 8000
    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 20000}],
    }, headers=h)
    body = r.json()
    assert float(body["change_amount"]) == 8000


@pytest.mark.asyncio
async def test_complete_invoice_multi_payment(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p2"]["id"], "quantity": 2}],
    }, headers=h)).json()
    # Total 50000 = 30000 cash + 20000 bank
    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [
            {"method": "CASH", "amount": 30000},
            {"method": "BANK_TRANSFER", "amount": 20000},
        ],
    }, headers=h)
    body = r.json()
    assert body["status"] == "COMPLETED"
    assert len(body["payments"]) == 2
    methods = {p["method"] for p in body["payments"]}
    assert methods == {"CASH", "BANK_TRANSFER"}


@pytest.mark.asyncio
async def test_complete_invoice_insufficient_stock(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1000}],  # tồn chỉ 100
    }, headers=h)).json()

    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "INSUFFICIENT_STOCK"
    assert "shortages" in body["error"]["details"]


@pytest.mark.asyncio
async def test_complete_invoice_updates_customer_stats(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": shop["customer"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 2}],
    }, headers=h)).json()

    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)

    c = (await client.get(
        f"/api/v1/customers/{shop['customer']['id']}", headers=h
    )).json()["customer"]
    assert float(c["total_spent"]) == 2 * 12000
    assert c["total_orders"] == 1
    assert c["last_order_at"] is not None


@pytest.mark.asyncio
async def test_complete_invoice_twice_rejected(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()

    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)
    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVOICE_NOT_DRAFT"


@pytest.mark.asyncio
async def test_complete_invoice_no_items(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [],
    }, headers=h)).json()

    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 1000}],
    }, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVOICE_NO_ITEMS"


# ===================================================================
# CANCEL
# ===================================================================

@pytest.mark.asyncio
async def test_cancel_draft_invoice(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()

    r = await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={
        "reason": "Khách đổi ý",
    }, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "CANCELLED"
    assert body["cancelled_at"] is not None
    assert body["cancel_reason"] == "Khách đổi ý"


@pytest.mark.asyncio
async def test_cancel_completed_invoice_rollbacks_stock_and_customer(
    client, shop
):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": shop["customer"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 5}],
    }, headers=h)).json()

    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)
    # Trước hủy: tồn 95
    r = await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={
        "reason": "Trả hàng",
    }, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "CANCELLED"

    # Stock restored: 100 - 5 + 5 = 100
    inv_list = (await client.get("/api/v1/inventory", headers=h)).json()
    p1_row = next(i for i in inv_list["items"] if i["product_id"] == shop["p1"]["id"])
    assert float(p1_row["quantity"]) == 100

    # Customer stats reverted
    c = (await client.get(
        f"/api/v1/customers/{shop['customer']['id']}", headers=h
    )).json()["customer"]
    assert float(c["total_spent"]) == 0
    assert c["total_orders"] == 0


@pytest.mark.asyncio
async def test_cancel_already_cancelled_rejected(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={}, headers=h)
    r = await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={}, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "ALREADY_CANCELLED"


@pytest.mark.asyncio
async def test_cashier_cannot_cancel_completed_invoice(client, registered_owner):
    """CASHIER không có quyền hủy hóa đơn đã COMPLETED."""
    owner_h = _auth(registered_owner["access_token"])
    # Tạo SP + tồn kho
    p1 = (await client.post("/api/v1/products", json={
        "name": "SP1", "sku": "SP-1", "sale_price": 10000, "cost_price": 5000,
    }, headers=owner_h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p1["id"], "quantity": 10, "cost_price": 5000}],
        "paid_amount": 10 * 5000,
    }, headers=owner_h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=owner_h)

    # Tạo cashier
    staff_resp = await client.post("/api/v1/staff", json={
        "full_name": "Cashier",
        "phone": "0911222333",
        "password": "secret123",
    }, headers=owner_h)
    assert staff_resp.status_code == 201, staff_resp.text

    cashier_login = await client.post("/api/v1/auth/login", json={
        "phone": "0911222333", "password": "secret123",
    })
    cashier_h = _auth(cashier_login.json()["access_token"])

    # Owner tạo + complete invoice
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": p1["id"], "quantity": 1}],
    }, headers=owner_h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=owner_h)

    # Cashier cố hủy → bị từ chối
    r = await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={
        "reason": "test",
    }, headers=cashier_h)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_CANCEL_COMPLETED"


@pytest.mark.asyncio
async def test_cashier_cannot_cancel_others_draft(client, registered_owner):
    owner_h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={
        "name": "SP1", "sku": "SP-2", "sale_price": 10000, "cost_price": 5000,
    }, headers=owner_h)).json()
    staff_resp = await client.post("/api/v1/staff", json={
        "full_name": "Cashier B", "phone": "0911222444", "password": "secret123",
    }, headers=owner_h)
    assert staff_resp.status_code == 201, staff_resp.text
    login_resp = await client.post("/api/v1/auth/login", json={
        "phone": "0911222444", "password": "secret123",
    })
    assert login_resp.status_code == 200, login_resp.text
    cashier_h = _auth(login_resp.json()["access_token"])

    # Owner tạo draft
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": p1["id"], "quantity": 1}],
    }, headers=owner_h)).json()

    r = await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={}, headers=cashier_h)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN_CANCEL_OTHERS_DRAFT"


# ===================================================================
# LIST / GET
# ===================================================================

@pytest.mark.asyncio
async def test_list_invoices_pagination(client, shop):
    h = shop["headers"]
    for _ in range(5):
        await client.post("/api/v1/invoices", json={
            "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
        }, headers=h)

    r = await client.get("/api/v1/invoices?page=1&limit=3", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] >= 5
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_list_invoices_filter_by_status(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)

    r = await client.get("/api/v1/invoices?status=COMPLETED", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert all(it["status"] == "COMPLETED" for it in body["items"])


@pytest.mark.asyncio
async def test_list_drafts(client, shop):
    h = shop["headers"]
    await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)
    await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p2"]["id"], "quantity": 1}],
    }, headers=h)

    r = await client.get("/api/v1/invoices/drafts", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) >= 2
    assert all(it["status"] == "DRAFT" for it in body["items"])


@pytest.mark.asyncio
async def test_get_invoice_detail(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()

    r = await client.get(f"/api/v1/invoices/{inv['id']}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == inv["id"]
    assert body["code"] == inv["code"]
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_invoice_tenant_isolation(client):
    """Tenant A KHÔNG được thấy invoice của tenant B."""
    # Register 2 shops
    a = (await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "owner_name": "OA",
        "phone": "0901111111", "password": "secret123",
    })).json()
    b = (await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "owner_name": "OB",
        "phone": "0902222222", "password": "secret123",
    })).json()
    h_a = _auth(a["access_token"])
    h_b = _auth(b["access_token"])

    # Shop A tạo SP + invoice
    p = (await client.post("/api/v1/products", json={
        "name": "P", "sku": "PX", "sale_price": 1000, "cost_price": 500,
    }, headers=h_a)).json()
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": p["id"], "quantity": 1}],
    }, headers=h_a)).json()

    # Shop B không thấy
    r = await client.get(f"/api/v1/invoices/{inv['id']}", headers=h_b)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_invoice_requires_auth(client):
    r = await client.get("/api/v1/invoices")
    assert r.status_code == 401


# ===================================================================
# SETTINGS — allow_debt từ tenant.settings
# ===================================================================

@pytest.mark.asyncio
async def test_tenant_settings_allow_debt(client, shop, db_session):
    """Khi tenant.settings.allow_debt=true → KHÔNG cần allow_debt trong payload."""
    from backend.modules.tenant.models import Tenant
    from sqlalchemy import select

    # Set allow_debt = true cho tenant
    tenant = (await db_session.execute(
        select(Tenant).where(Tenant.id == shop["tenant_id"])
    )).scalar_one()
    tenant.settings = {"allow_debt": True}
    await db_session.commit()

    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": shop["customer"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 5}],
    }, headers=h)).json()

    # Pay 1000 < total 60000 — nhưng allow_debt là true từ tenant.settings
    r = await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 1000}],
    }, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "COMPLETED"
