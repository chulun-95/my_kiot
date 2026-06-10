import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_product_unit_model_exists(client, registered_owner):
    """ProductUnit table must exist — creating a product should return units=[]."""
    h = _auth(registered_owner["access_token"])
    r = await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "units" in body
    assert body["units"] == []


@pytest.mark.asyncio
async def test_create_product_unit_schema_validation(client, registered_owner):
    """POST /products/{id}/units requires conversion_rate > 1."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()

    r = await client.post(
        f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "lon", "conversion_rate": 1.0},
        headers=h,
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_create_product_unit(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()

    r = await client.post(
        f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "sale_price": 240000, "barcode": "8934563012345"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    u = r.json()
    assert u["unit_name"] == "thùng"
    assert float(u["conversion_rate"]) == 24.0
    assert float(u["sale_price"]) == 240000.0
    assert u["barcode"] == "8934563012345"


@pytest.mark.asyncio
async def test_list_product_units_in_product_response(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )

    r = await client.get(f"/api/v1/products/{p['id']}", headers=h)
    assert r.status_code == 200
    units = r.json()["units"]
    assert len(units) == 1
    assert units[0]["unit_name"] == "thùng"


@pytest.mark.asyncio
async def test_barcode_lookup_via_product_unit(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "barcode": "1111111111111"},
        headers=h,
    )

    r = await client.get("/api/v1/products/barcode/1111111111111", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == p["id"]
    assert body["matched_unit"] is not None
    assert body["matched_unit"]["unit_name"] == "thùng"


@pytest.mark.asyncio
async def test_delete_product_unit_blocked_by_draft(client, registered_owner):
    """Cannot delete unit if a DRAFT receipt uses it."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    # Create DRAFT receipt using this unit
    await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
    }, headers=h)

    r = await client.delete(f"/api/v1/products/{p['id']}/units/{u['id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "UNIT_IN_USE"


@pytest.mark.asyncio
async def test_goods_receipt_with_unit_converts_to_base(client, registered_owner):
    """2 thùng × 24 = 48 lon. Inventory must show 48."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia Sài Gòn", "unit": "lon", "sale_price": 10000, "cost_price": 0},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
        "paid_amount": 2 * 240000,
    }, headers=h)).json()

    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert float(item["quantity"]) == 48.0


@pytest.mark.asyncio
async def test_goods_receipt_cost_per_base_unit(client, registered_owner):
    """cost_per_base = 240,000 / 24 = 10,000/lon."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Pepsi", "unit": "lon", "sale_price": 10000, "cost_price": 0},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
        "paid_amount": 2 * 240000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    r = await client.get(f"/api/v1/products/{p['id']}", headers=h)
    assert float(r.json()["cost_price"]) == 10000.0


@pytest.mark.asyncio
async def test_invoice_with_unit_deducts_base_qty(client, registered_owner):
    """Sell 1 thùng (×24). Inventory should decrease by 24 lon."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Coca", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "sale_price": 240000},
        headers=h,
    )).json()

    # Stock up 48 lon
    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 48, "cost_price": 8000}],
        "paid_amount": 48 * 8000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    # Sell 1 thùng
    inv_data = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 1, "unit_price": 240000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv_data['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 240000}],
    }, headers=h)

    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert float(item["quantity"]) == 24.0  # 48 - 24 = 24


@pytest.mark.asyncio
async def test_inventory_units_breakdown(client, registered_owner):
    """Inventory response should show units_breakdown."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 48, "cost_price": 8000}],
        "paid_amount": 48 * 8000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert "units_breakdown" in item
    breakdown = item["units_breakdown"]
    assert len(breakdown) == 1
    assert breakdown[0]["unit_name"] == "thùng"
    assert float(breakdown[0]["conversion_rate"]) == 24.0
    assert float(breakdown[0]["quantity_in_unit"]) == 2.0  # 48 / 24


@pytest.mark.asyncio
async def test_product_unit_duplicate_unit_name(client, registered_owner):
    """Cannot create two units with the same name for the same product."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000},
        headers=h,
    )).json()
    await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )
    r = await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 12},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_product_unit_duplicate_barcode_cross_product(client, registered_owner):
    """Barcode must be unique within tenant across all products."""
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={"name": "P1", "sale_price": 1000}, headers=h)).json()
    p2 = (await client.post("/api/v1/products", json={"name": "P2", "sale_price": 1000}, headers=h)).json()
    await client.post(f"/api/v1/products/{p1['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "barcode": "SHARED-BC"},
        headers=h,
    )
    r = await client.post(f"/api/v1/products/{p2['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24, "barcode": "SHARED-BC"},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_update_product_unit(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={"name": "Bia", "unit": "lon", "sale_price": 10000}, headers=h)).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    r = await client.put(f"/api/v1/products/{p['id']}/units/{u['id']}",
        json={"sale_price": 250000},
        headers=h,
    )
    assert r.status_code == 200
    assert float(r.json()["sale_price"]) == 250000.0
    assert r.json()["unit_name"] == "thùng"  # unchanged


@pytest.mark.asyncio
async def test_delete_product_unit_success(client, registered_owner):
    """Can delete unit when no DRAFT transactions use it."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={"name": "Bia", "unit": "lon", "sale_price": 10000}, headers=h)).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    r = await client.delete(f"/api/v1/products/{p['id']}/units/{u['id']}", headers=h)
    assert r.status_code == 200

    r2 = await client.get(f"/api/v1/products/{p['id']}/units", headers=h)
    assert r2.json() == []


@pytest.mark.asyncio
async def test_cashier_cannot_create_unit(client, registered_owner):
    """CASHIER role must get 403 on POST /products/{id}/units."""
    h_owner = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={"name": "Bia", "unit": "lon", "sale_price": 10000}, headers=h_owner)).json()

    # Create a cashier
    cashier_resp = await client.post("/api/v1/staff", json={
        "full_name": "Cashier Test",
        "phone": "0987654321",
        "password": "secret123",
        "role": "CASHIER",
    }, headers=h_owner)
    assert cashier_resp.status_code == 201, cashier_resp.text

    login = await client.post("/api/v1/auth/login", json={
        "phone": "0987654321",
        "password": "secret123",
    })
    h_cashier = _auth(login.json()["access_token"])

    r = await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h_cashier,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cancel_completed_receipt_with_unit_restores_base_qty(client, registered_owner):
    """Cancel completed receipt → stock restored by base_qty."""
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products",
        json={"name": "Bia", "unit": "lon", "sale_price": 10000, "cost_price": 8000},
        headers=h,
    )).json()
    u = (await client.post(f"/api/v1/products/{p['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()

    receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "unit_id": u["id"], "quantity": 2, "cost_price": 240000}],
        "paid_amount": 2 * 240000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/complete", headers=h)

    # Verify stock = 48
    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    item = next(i for i in inv["items"] if i["product_id"] == p["id"])
    assert float(item["quantity"]) == 48.0

    await client.post(f"/api/v1/goods-receipts/{receipt['id']}/cancel",
        json={"reason": "Test"}, headers=h)

    inv2 = (await client.get("/api/v1/inventory", headers=h)).json()
    item2 = next(i for i in inv2["items"] if i["product_id"] == p["id"])
    assert float(item2["quantity"]) == 0.0
