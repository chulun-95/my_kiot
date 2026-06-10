"""Tests cho audit logging, price history, stocktake và tenant settings."""
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.modules.system.models import AuditLog, PriceHistory


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def shop(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={
        "name": "P1", "sku": "P1", "sale_price": 10000, "cost_price": 5000,
    }, headers=h)).json()
    return {
        "headers": h,
        "p1": p1,
        "user_id": registered_owner["user"]["id"],
        "tenant_id": registered_owner["tenant"]["id"],
    }


# ===================================================================
# AUDIT LOGS
# ===================================================================

@pytest.mark.asyncio
async def test_create_product_writes_audit(client, shop, db_session):
    h = shop["headers"]
    p = (await client.post("/api/v1/products", json={
        "name": "Audited", "sku": "AUD-1", "sale_price": 1000, "cost_price": 500,
    }, headers=h)).json()

    logs = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.tenant_id == shop["tenant_id"],
            AuditLog.action == "CREATE_PRODUCT",
            AuditLog.entity_id == p["id"],
        )
    )).scalars().all()
    assert len(logs) == 1
    assert logs[0].new_data["sku"] == "AUD-1"
    assert logs[0].new_data["name"] == "Audited"


@pytest.mark.asyncio
async def test_update_product_writes_diff_audit(client, shop, db_session):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    await client.put(f"/api/v1/products/{pid}", json={
        "sale_price": 15000, "name": "P1 Updated",
    }, headers=h)

    logs = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "UPDATE_PRODUCT",
            AuditLog.entity_id == pid,
        )
    )).scalars().all()
    assert len(logs) == 1
    assert "sale_price" in logs[0].new_data
    assert "name" in logs[0].new_data
    assert "cost_price" not in logs[0].new_data  # không thay đổi → không ghi


@pytest.mark.asyncio
async def test_complete_invoice_writes_audit(client, shop, db_session):
    h = shop["headers"]
    # Nhập hàng + bán
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 5000}],
        "paid_amount": 10 * 5000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)

    logs = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "COMPLETE_INVOICE",
            AuditLog.entity_id == inv["id"],
        )
    )).scalars().all()
    assert len(logs) == 1
    assert logs[0].new_data["code"] == inv["code"]


@pytest.mark.asyncio
async def test_create_staff_writes_audit(client, registered_owner, db_session):
    h = _auth(registered_owner["access_token"])
    resp = await client.post("/api/v1/staff", json={
        "full_name": "Audited Staff", "phone": "0912333444", "password": "secret123",
    }, headers=h)
    assert resp.status_code == 201
    staff_id = resp.json()["id"]

    logs = (await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "CREATE_STAFF",
            AuditLog.entity_id == staff_id,
        )
    )).scalars().all()
    assert len(logs) == 1
    assert logs[0].new_data["full_name"] == "Audited Staff"


# ===================================================================
# PRICE HISTORY
# ===================================================================

@pytest.mark.asyncio
async def test_manual_price_change_writes_history(client, shop, db_session):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    await client.put(f"/api/v1/products/{pid}", json={
        "sale_price": 20000,
    }, headers=h)

    rows = (await db_session.execute(
        select(PriceHistory).where(
            PriceHistory.product_id == pid,
            PriceHistory.field == "sale_price",
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].ref_type == "MANUAL"
    assert Decimal(rows[0].new_value) == Decimal("20000")
    assert Decimal(rows[0].old_value) == Decimal("10000")


@pytest.mark.asyncio
async def test_same_price_no_history(client, shop, db_session):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    # Cập nhật tên — không động đến giá
    await client.put(f"/api/v1/products/{pid}", json={"name": "Renamed"}, headers=h)

    rows = (await db_session.execute(
        select(PriceHistory).where(PriceHistory.product_id == pid)
    )).scalars().all()
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_goods_receipt_writes_price_history_on_cost_change(
    client, shop, db_session
):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    # Nhập 10 cái giá 8000 (khác cost cũ 5000) → giá vốn bình quân thay đổi
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": pid, "quantity": 10, "cost_price": 8000}],
        "paid_amount": 10 * 8000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    rows = (await db_session.execute(
        select(PriceHistory).where(
            PriceHistory.product_id == pid,
            PriceHistory.field == "cost_price",
            PriceHistory.ref_type == "GOODS_RECEIPT",
        )
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].ref_id == r["id"]


# ===================================================================
# STOCKTAKE / ADJUSTMENT
# ===================================================================

@pytest.mark.asyncio
async def test_create_adjustment(client, shop, db_session):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    # Nhập 10 cái trước
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": pid, "quantity": 10, "cost_price": 5000}],
        "paid_amount": 10 * 5000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    # Kiểm kê thấy chỉ còn 7 (mất 3)
    resp = await client.post("/api/v1/inventory/adjustments", json={
        "items": [{"product_id": pid, "new_quantity": 7, "reason": "Kiểm kê thiếu 3"}],
    }, headers=h)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert float(item["old_quantity"]) == 10
    assert float(item["new_quantity"]) == 7
    assert float(item["delta"]) == -3

    # Inventory đã cập nhật
    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    p1_row = next(i for i in inv["items"] if i["product_id"] == pid)
    assert float(p1_row["quantity"]) == 7

    # Stock movement type=ADJUSTMENT
    mv = (await client.get(f"/api/v1/inventory/{pid}/movements", headers=h)).json()
    adj = [m for m in mv["items"] if m["type"] == "ADJUSTMENT"]
    assert len(adj) == 1
    assert float(adj[0]["quantity"]) == -3


@pytest.mark.asyncio
async def test_adjustment_owner_only(client, registered_owner):
    owner_h = _auth(registered_owner["access_token"])
    # Tạo cashier
    await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0911333444", "password": "secret123",
    }, headers=owner_h)
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0911333444", "password": "secret123",
    })).json()["access_token"]

    p = (await client.post("/api/v1/products", json={
        "name": "P", "sku": "P-AD", "sale_price": 1000, "cost_price": 500,
    }, headers=owner_h)).json()

    r = await client.post("/api/v1/inventory/adjustments", json={
        "items": [{"product_id": p["id"], "new_quantity": 5}],
    }, headers=_auth(cashier_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_adjustment_negative_not_allowed(client, shop):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    # p1 không cho phép âm
    r = await client.post("/api/v1/inventory/adjustments", json={
        "items": [{"product_id": pid, "new_quantity": -5}],
    }, headers=h)
    assert r.status_code == 422  # pydantic ge=0 chặn trước


@pytest.mark.asyncio
async def test_adjustment_duplicate_product_rejected(client, shop):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    r = await client.post("/api/v1/inventory/adjustments", json={
        "items": [
            {"product_id": pid, "new_quantity": 5},
            {"product_id": pid, "new_quantity": 10},
        ],
    }, headers=h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "DUPLICATE_PRODUCT"


@pytest.mark.asyncio
async def test_list_adjustments(client, shop):
    h = shop["headers"]
    pid = shop["p1"]["id"]
    await client.post("/api/v1/inventory/adjustments", json={
        "items": [{"product_id": pid, "new_quantity": 3, "reason": "Mất hàng"}],
    }, headers=h)
    r = await client.get("/api/v1/inventory/adjustments", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] >= 1
    assert body["items"][0]["product_sku"] == "P1"


# ===================================================================
# TENANT SETTINGS — cost visibility
# ===================================================================

@pytest.mark.asyncio
async def test_cashier_cannot_see_cost_by_default(client, registered_owner):
    owner_h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "P", "sku": "P-COST", "sale_price": 1000, "cost_price": 500,
    }, headers=owner_h)).json()

    # Tạo cashier
    await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0911555666", "password": "secret123",
    }, headers=owner_h)
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0911555666", "password": "secret123",
    })).json()["access_token"]

    # Cashier xem chi tiết SP — cost_price phải bị ẩn (None)
    r = await client.get(
        f"/api/v1/products/{p['id']}", headers=_auth(cashier_token)
    )
    assert r.status_code == 200
    assert r.json()["cost_price"] is None
    assert r.json()["sale_price"] == "1000.00"

    # Owner xem cùng SP — vẫn thấy cost
    r2 = await client.get(f"/api/v1/products/{p['id']}", headers=owner_h)
    assert r2.json()["cost_price"] == "500.00"


@pytest.mark.asyncio
async def test_cashier_can_see_cost_when_setting_enabled(
    client, registered_owner, db_session
):
    from backend.modules.tenant.models import Tenant

    owner_h = _auth(registered_owner["access_token"])
    tenant_id = registered_owner["tenant"]["id"]
    # Bật show_cost_to_cashier
    tenant = (await db_session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )).scalar_one()
    tenant.settings = {"show_cost_to_cashier": True}
    await db_session.commit()

    p = (await client.post("/api/v1/products", json={
        "name": "P", "sku": "P-COST-2", "sale_price": 1000, "cost_price": 500,
    }, headers=owner_h)).json()

    staff_resp = await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0911777888", "password": "secret123",
    }, headers=owner_h)
    assert staff_resp.status_code == 201, staff_resp.text
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0911777888", "password": "secret123",
    })).json()["access_token"]

    r = await client.get(
        f"/api/v1/products/{p['id']}", headers=_auth(cashier_token)
    )
    assert r.json()["cost_price"] == "500.00"
