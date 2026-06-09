import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- fixtures ----------

@pytest.fixture
async def shop(client, registered_owner):
    """Owner + 2 sản phẩm + 1 NCC sẵn sàng."""
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={
        "name": "Coca 330ml", "sku": "COC-330", "sale_price": 12000, "cost_price": 9000,
    }, headers=h)).json()
    p2 = (await client.post("/api/v1/products", json={
        "name": "Pepsi 1.5L", "sku": "PEP-1500", "sale_price": 25000, "cost_price": 20000,
    }, headers=h)).json()
    s = (await client.post("/api/v1/suppliers", json={
        "name": "NCC Coca Co",
    }, headers=h)).json()
    return {
        "headers": h,
        "p1": p1,
        "p2": p2,
        "supplier": s,
        "token": registered_owner["access_token"],
    }


# ---------- Create / Update ----------

@pytest.mark.asyncio
async def test_create_goods_receipt_draft(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [
            {"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000},
            {"product_id": shop["p2"]["id"], "quantity": 5, "cost_price": 20000},
        ],
        "note": "Phiếu nhập đầu kỳ",
    }, headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["code"].startswith("NK")
    assert body["status"] == "DRAFT"
    assert float(body["total"]) == 10 * 9000 + 5 * 20000
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_create_receipt_invalid_product(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": 99999, "quantity": 1, "cost_price": 100}],
    }, headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_receipt_invalid_supplier(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/goods-receipts", json={
        "supplier_id": 99999,
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1, "cost_price": 100}],
    }, headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_receipt_empty_items(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/goods-receipts", json={"items": []}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_receipt_negative_quantity(client, shop):
    h = shop["headers"]
    r = await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": -1, "cost_price": 1000}],
    }, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_draft_receipt(client, shop):
    h = shop["headers"]
    r1 = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 5, "cost_price": 9000}],
    }, headers=h)).json()

    r2 = await client.put(f"/api/v1/goods-receipts/{r1['id']}", json={
        "items": [
            {"product_id": shop["p1"]["id"], "quantity": 8, "cost_price": 8500},
            {"product_id": shop["p2"]["id"], "quantity": 3, "cost_price": 20000},
        ],
        "note": "Sửa số lượng",
    }, headers=h)
    assert r2.status_code == 200
    body = r2.json()
    assert len(body["items"]) == 2
    assert float(body["total"]) == 8 * 8500 + 3 * 20000


# ---------- Complete ----------

@pytest.mark.asyncio
async def test_complete_receipt_updates_stock(client, shop):
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [
            {"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000},
            {"product_id": shop["p2"]["id"], "quantity": 5, "cost_price": 20000},
        ],
    }, headers=h)).json()

    r2 = await client.post(
        f"/api/v1/goods-receipts/{r['id']}/complete", headers=h
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "COMPLETED"
    assert r2.json()["completed_at"] is not None

    # Inventory updated
    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    p1_inv = next(i for i in inv["items"] if i["product_id"] == shop["p1"]["id"])
    p2_inv = next(i for i in inv["items"] if i["product_id"] == shop["p2"]["id"])
    assert float(p1_inv["quantity"]) == 10.0
    assert float(p2_inv["quantity"]) == 5.0


@pytest.mark.asyncio
async def test_complete_receipt_average_cost(client, shop):
    """Nhập 10@9000 rồi 10@11000 → giá vốn bình quân = 10000."""
    h = shop["headers"]
    r1 = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r1['id']}/complete", headers=h)

    r2 = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 11000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r2['id']}/complete", headers=h)

    p = (await client.get(f"/api/v1/products/{shop['p1']['id']}", headers=h)).json()
    assert float(p["cost_price"]) == 10000.0  # bình quân (10*9000 + 10*11000) / 20


@pytest.mark.asyncio
async def test_complete_receipt_twice_rejected(client, shop):
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1, "cost_price": 1000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    r2 = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "RECEIPT_NOT_DRAFT"


@pytest.mark.asyncio
async def test_update_completed_receipt_rejected(client, shop):
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1, "cost_price": 1000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    r2 = await client.put(f"/api/v1/goods-receipts/{r['id']}", json={
        "note": "Try update",
    }, headers=h)
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_complete_receipt_debt_without_supplier_rejected(client, shop):
    """Nhập nợ (trả thiếu) khi chưa chọn NCC phải bị chặn — nợ sẽ không thống kê được."""
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000}],
        "paid_amount": 0,
    }, headers=h)).json()

    r2 = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "DEBT_REQUIRES_SUPPLIER"


@pytest.mark.asyncio
async def test_complete_receipt_debt_with_supplier_ok(client, shop):
    """Nhập nợ có NCC → cho phép (công nợ phải trả được thống kê)."""
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000}],
        "paid_amount": 0,
    }, headers=h)).json()

    r2 = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "COMPLETED"


# ---------- Cancel ----------

@pytest.mark.asyncio
async def test_cancel_draft_receipt(client, shop):
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 5, "cost_price": 9000}],
    }, headers=h)).json()
    r2 = await client.post(
        f"/api/v1/goods-receipts/{r['id']}/cancel",
        json={"reason": "Sai NCC"},
        headers=h,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_completed_receipt_rollbacks_stock(client, shop):
    h = shop["headers"]
    # nhập 10 cái
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    # cancel
    r2 = await client.post(
        f"/api/v1/goods-receipts/{r['id']}/cancel",
        json={"reason": "Sai dữ liệu"},
        headers=h,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "CANCELLED"

    # stock về 0
    movs = (await client.get(
        f"/api/v1/inventory/{shop['p1']['id']}/movements", headers=h
    )).json()
    # ít nhất 1 RECEIPT và 1 CANCEL_RECEIPT
    types = [m["type"] for m in movs["items"]]
    assert "RECEIPT" in types
    assert "CANCEL_RECEIPT" in types

    inv = (await client.get("/api/v1/inventory", headers=h)).json()
    p1_inv = next((i for i in inv["items"] if i["product_id"] == shop["p1"]["id"]), None)
    if p1_inv is not None:
        assert float(p1_inv["quantity"]) == 0.0


@pytest.mark.asyncio
async def test_cancel_already_cancelled_rejected(client, shop):
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1, "cost_price": 1000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/cancel", json={}, headers=h)
    r2 = await client.post(f"/api/v1/goods-receipts/{r['id']}/cancel", json={}, headers=h)
    assert r2.status_code == 400


# ---------- Inventory queries ----------

@pytest.mark.asyncio
async def test_inventory_list_empty_initial(client, shop):
    h = shop["headers"]
    r = await client.get("/api/v1/inventory", headers=h)
    assert r.status_code == 200
    # Chưa nhập kho → có thể trống hoặc 0
    items = r.json()["items"]
    assert all(float(i["quantity"]) == 0.0 for i in items)


@pytest.mark.asyncio
async def test_inventory_movements_kardex(client, shop):
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 7, "cost_price": 9000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    movs = await client.get(
        f"/api/v1/inventory/{shop['p1']['id']}/movements", headers=h
    )
    assert movs.status_code == 200
    items = movs.json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == "RECEIPT"
    assert float(items[0]["quantity"]) == 7.0
    assert float(items[0]["balance_after"]) == 7.0


@pytest.mark.asyncio
async def test_inventory_movements_invalid_product(client, shop):
    h = shop["headers"]
    r = await client.get("/api/v1/inventory/99999/movements", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_low_stock_endpoint(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p_low = (await client.post("/api/v1/products", json={
        "name": "Low item", "sale_price": 1000, "min_stock": 10,
    }, headers=h)).json()
    p_out = (await client.post("/api/v1/products", json={
        "name": "Out item", "sale_price": 1000, "min_stock": 5,
    }, headers=h)).json()

    # nhập 5 cho p_low (dưới min 10 → LOW); p_out không nhập (tồn 0 → OUT_OF_STOCK)
    # trả đủ tiền (paid = total) nên không cần NCC
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p_low["id"], "quantity": 5, "cost_price": 100}],
        "paid_amount": 5 * 100,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    low = await client.get("/api/v1/inventory/low-stock", headers=h)
    assert low.status_code == 200
    body = low.json()
    by_pid = {i["product_id"]: i for i in body["items"]}
    assert by_pid[p_low["id"]]["severity"] == "LOW"
    assert float(by_pid[p_low["id"]]["shortage"]) == 5.0
    assert by_pid[p_out["id"]]["severity"] == "OUT_OF_STOCK"
    assert float(by_pid[p_out["id"]]["shortage"]) == 5.0
    assert body["summary"]["out_of_stock_count"] >= 1
    assert body["summary"]["low_count"] >= 1
    assert body["summary"]["total_count"] == (
        body["summary"]["out_of_stock_count"] + body["summary"]["low_count"]
    )


@pytest.mark.asyncio
async def test_low_stock_endpoint_forbidden_for_cashier(client, registered_owner):
    """CASHIER không được xem cảnh báo tồn — chỉ OWNER mới có quyền."""
    owner_h = _auth(registered_owner["access_token"])
    # Tạo CASHIER + login
    await client.post(
        "/api/v1/staff",
        json={
            "full_name": "Cashier", "phone": "0987111111", "password": "cashier123",
        },
        headers=owner_h,
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0987111111", "password": "cashier123"},
    )
    cashier_h = _auth(login.json()["access_token"])

    r = await client.get("/api/v1/inventory/low-stock", headers=cashier_h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_inventory_cost_hidden_from_cashier(client, shop):
    """CASHIER không thấy giá vốn ở màn Tồn kho; OWNER thì thấy."""
    h = shop["headers"]
    # nhập kho để có dòng inventory (gắn NCC để complete không bị chặn nợ)
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000}],
    }, headers=h)).json()
    rc = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert rc.status_code == 200, rc.text

    # OWNER thấy cost_price
    owner_list = (await client.get("/api/v1/inventory", headers=h)).json()
    row = next(i for i in owner_list["items"] if i["product_id"] == shop["p1"]["id"])
    assert row["cost_price"] is not None and float(row["cost_price"]) == 9000

    # CASHIER không thấy (mặc định show_cost_to_cashier = false)
    await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0987222333", "password": "cashier123",
    }, headers=h)
    login = await client.post("/api/v1/auth/login", json={
        "phone": "0987222333", "password": "cashier123",
    })
    cashier_h = _auth(login.json()["access_token"])
    cashier_list = (await client.get("/api/v1/inventory", headers=cashier_h)).json()
    crow = next(i for i in cashier_list["items"] if i["product_id"] == shop["p1"]["id"])
    assert crow["cost_price"] is None
    # nhưng vẫn thấy số lượng + giá bán
    assert float(crow["quantity"]) == 10
    assert float(crow["sale_price"]) == 12000


@pytest.mark.asyncio
async def test_receipt_payment_method_flows_to_cashbook(client, shop):
    """Phương thức trả tiền nhập phải ghi đúng vào sổ quỹ (không hardcode CASH)."""
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 9000}],
        "paid_amount": 90000,
        "payment_method": "BANK_TRANSFER",
    }, headers=h)).json()
    assert r["payment_method"] == "BANK_TRANSFER"
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    cash = (await client.get("/api/v1/cash-transactions?ref_type=GOODS_RECEIPT", headers=h)).json()
    entry = next(i for i in cash["items"] if i["category"] == "PURCHASE")
    assert entry["method"] == "BANK_TRANSFER"
    assert float(entry["amount"]) == 90000


# ---------- List receipts ----------

@pytest.mark.asyncio
async def test_list_receipts_pagination(client, shop):
    h = shop["headers"]
    for _ in range(5):
        await client.post("/api/v1/goods-receipts", json={
            "items": [{"product_id": shop["p1"]["id"], "quantity": 1, "cost_price": 1000}],
        }, headers=h)

    r = await client.get("/api/v1/goods-receipts?page=1&limit=3", headers=h)
    body = r.json()
    assert body["pagination"]["total"] == 5
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_list_receipts_filter_by_status(client, shop):
    h = shop["headers"]
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": shop["supplier"]["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1, "cost_price": 1000}],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1, "cost_price": 1000}],
    }, headers=h)  # vẫn DRAFT

    completed = await client.get(
        "/api/v1/goods-receipts?status=COMPLETED", headers=h
    )
    assert all(i["status"] == "COMPLETED" for i in completed.json()["items"])


# ---------- Tenant isolation ----------

@pytest.mark.asyncio
async def test_receipt_tenant_isolation(client):
    rA = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "owner_name": "Owner A",
        "phone": "0911111111", "password": "secret123",
    })
    rB = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "owner_name": "Owner B",
        "phone": "0922222222", "password": "secret123",
    })
    tokA = rA.json()["access_token"]
    tokB = rB.json()["access_token"]

    pA = (await client.post("/api/v1/products", json={
        "name": "A item", "sale_price": 1000,
    }, headers=_auth(tokA))).json()
    rA_receipt = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": pA["id"], "quantity": 1, "cost_price": 100}],
    }, headers=_auth(tokA))).json()

    # B not see A's receipt
    r = await client.get(
        f"/api/v1/goods-receipts/{rA_receipt['id']}", headers=_auth(tokB)
    )
    assert r.status_code == 404

    # B not complete A's receipt
    r2 = await client.post(
        f"/api/v1/goods-receipts/{rA_receipt['id']}/complete",
        headers=_auth(tokB),
    )
    assert r2.status_code == 404
