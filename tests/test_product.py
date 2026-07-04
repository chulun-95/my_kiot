import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_product_minimal(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post(
        "/api/v1/products",
        json={"name": "Coca 330ml", "sale_price": 12000, "cost_price": 9000},
        headers=h,
    )
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["name"] == "Coca 330ml"
    assert p["sku"].startswith("SP")  # auto sinh
    assert p["status"] == "ACTIVE"
    assert p["unit"] == "cái"


@pytest.mark.asyncio
async def test_create_product_full(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    cat = (await client.post(
        "/api/v1/categories", json={"name": "Đồ uống"}, headers=h
    )).json()

    payload = {
        "name": "Pepsi 1.5L",
        "sku": "PEPSI-1500",
        "barcode": "8934588063015",
        "category_id": cat["id"],
        "description": "Chai 1.5 lít",
        "unit": "chai",
        "cost_price": 20000,
        "sale_price": 25000,
        "min_stock": 10,
        "allow_negative": False,
    }
    r = await client.post("/api/v1/products", json=payload, headers=h)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["sku"] == "PEPSI-1500"
    assert p["barcode"] == "8934588063015"
    assert p["category_id"] == cat["id"]
    assert p["category_name"] == "Đồ uống"
    assert float(p["sale_price"]) == 25000.0


@pytest.mark.asyncio
async def test_create_product_duplicate_sku(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = {"name": "X", "sku": "SKU-A", "sale_price": 1000}
    r1 = await client.post("/api/v1/products", json=p, headers=h)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/products", json={**p, "name": "Y"}, headers=h)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] in {"SKU_EXISTS", "DUPLICATE"}


@pytest.mark.asyncio
async def test_create_product_duplicate_barcode(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r1 = await client.post("/api/v1/products", json={
        "name": "X", "barcode": "8934588000001", "sale_price": 1000,
    }, headers=h)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/products", json={
        "name": "Y", "barcode": "8934588000001", "sale_price": 1000,
    }, headers=h)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_product_negative_price_rejected(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post("/api/v1/products", json={
        "name": "X", "sale_price": -100,
    }, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_product_invalid_category(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post("/api/v1/products", json={
        "name": "X", "category_id": 99999, "sale_price": 1000,
    }, headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_product(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    created = (await client.post("/api/v1/products", json={
        "name": "Item", "sale_price": 5000,
    }, headers=h)).json()

    r = await client.get(f"/api/v1/products/{created['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Item"


@pytest.mark.asyncio
async def test_get_product_not_found(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.get("/api/v1/products/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_product(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "Old", "sale_price": 1000, "cost_price": 500,
    }, headers=h)).json()

    r = await client.put(
        f"/api/v1/products/{p['id']}",
        json={"name": "New", "sale_price": 2000, "min_stock": 5},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "New"
    assert float(body["sale_price"]) == 2000.0
    assert body["min_stock"] == 5
    # untouched
    assert float(body["cost_price"]) == 500.0


@pytest.mark.asyncio
async def test_update_product_sku_collision(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={
        "name": "P1", "sku": "AAA", "sale_price": 1000,
    }, headers=h)).json()
    p2 = (await client.post("/api/v1/products", json={
        "name": "P2", "sku": "BBB", "sale_price": 1000,
    }, headers=h)).json()

    r = await client.put(
        f"/api/v1/products/{p2['id']}",
        json={"sku": "AAA"},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_update_product_clear_category(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    cat = (await client.post(
        "/api/v1/categories", json={"name": "Đồ uống"}, headers=h
    )).json()
    p = (await client.post("/api/v1/products", json={
        "name": "Pepsi", "sale_price": 12000, "category_id": cat["id"],
    }, headers=h)).json()
    assert p["category_id"] == cat["id"]

    r = await client.put(
        f"/api/v1/products/{p['id']}",
        json={"category_id": None},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["category_id"] is None


@pytest.mark.asyncio
async def test_delete_product_soft(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "X", "sale_price": 1000,
    }, headers=h)).json()

    r = await client.delete(f"/api/v1/products/{p['id']}", headers=h)
    assert r.status_code == 200

    # Not visible in list
    lst = (await client.get("/api/v1/products", headers=h)).json()
    assert all(x["id"] != p["id"] for x in lst["items"])

    # GET returns 404
    r2 = await client.get(f"/api/v1/products/{p['id']}", headers=h)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_requires_owner(client, registered_owner):
    """CASHIER role must get 403 on DELETE /products/{id}."""
    h_owner = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "Bia", "unit": "lon", "sale_price": 10000,
    }, headers=h_owner)).json()

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

    r = await client.delete(f"/api/v1/products/{p['id']}", headers=h_cashier)
    assert r.status_code == 403

    # SP vẫn còn nguyên (chưa bị xóa)
    r2 = await client.get(f"/api/v1/products/{p['id']}", headers=h_owner)
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_list_products_pagination(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    for i in range(25):
        await client.post("/api/v1/products", json={
            "name": f"P{i}", "sale_price": 1000,
        }, headers=h)

    r = await client.get("/api/v1/products?page=1&limit=10", headers=h)
    body = r.json()
    assert body["pagination"]["total"] == 25
    assert body["pagination"]["total_pages"] == 3
    assert len(body["items"]) == 10

    r2 = await client.get("/api/v1/products?page=3&limit=10", headers=h)
    assert len(r2.json()["items"]) == 5


@pytest.mark.asyncio
async def test_list_products_filter_by_category(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    catA = (await client.post(
        "/api/v1/categories", json={"name": "A"}, headers=h
    )).json()
    catB = (await client.post(
        "/api/v1/categories", json={"name": "B"}, headers=h
    )).json()

    await client.post("/api/v1/products", json={
        "name": "PA", "category_id": catA["id"], "sale_price": 1000,
    }, headers=h)
    await client.post("/api/v1/products", json={
        "name": "PB", "category_id": catB["id"], "sale_price": 1000,
    }, headers=h)

    r = await client.get(
        f"/api/v1/products?category_id={catA['id']}", headers=h
    )
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "PA"


@pytest.mark.asyncio
async def test_list_products_search(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/products", json={
        "name": "Coca Cola 330ml", "sale_price": 12000,
    }, headers=h)
    await client.post("/api/v1/products", json={
        "name": "Pepsi 330ml", "sale_price": 11000,
    }, headers=h)

    r = await client.get("/api/v1/products?search=coca", headers=h)
    items = r.json()["items"]
    assert len(items) == 1
    assert "Coca" in items[0]["name"]


@pytest.mark.asyncio
async def test_search_products_endpoint(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/products", json={
        "name": "Sữa Vinamilk", "sku": "SVN-100", "sale_price": 30000,
    }, headers=h)
    await client.post("/api/v1/products", json={
        "name": "Mỳ tôm Hảo Hảo", "sku": "MYT-001", "sale_price": 4000,
    }, headers=h)
    # INACTIVE should be filtered out from POS search
    await client.post("/api/v1/products", json={
        "name": "Sữa Cũ", "status": "INACTIVE", "sale_price": 1000,
    }, headers=h)

    # Diacritic-insensitive: "sua" matches "Sữa Vinamilk"
    r = await client.get("/api/v1/products/search?q=sua", headers=h)
    items = r.json()["items"]
    assert any(i["name"] == "Sữa Vinamilk" for i in items)
    assert all(i["status"] == "ACTIVE" for i in items)

    # Diacritic-insensitive multi-word: "my tom" matches "Mỳ tôm Hảo Hảo"
    r2 = await client.get("/api/v1/products/search?q=my tom", headers=h)
    items2 = r2.json()["items"]
    assert any(i["name"] == "Mỳ tôm Hảo Hảo" for i in items2)

    # Exact with diacritic still works
    r3 = await client.get("/api/v1/products/search?q=Sữa", headers=h)
    items3 = r3.json()["items"]
    assert all(i["status"] == "ACTIVE" for i in items3)
    assert any(i["name"] == "Sữa Vinamilk" for i in items3)


@pytest.mark.asyncio
async def test_search_by_sku(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/products", json={
        "name": "Item", "sku": "CUSTOM-XYZ", "sale_price": 1000,
    }, headers=h)
    r = await client.get("/api/v1/products/search?q=XYZ", headers=h)
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "CUSTOM-XYZ"


@pytest.mark.asyncio
async def test_get_by_barcode(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/products", json={
        "name": "Coca", "barcode": "8934588000123", "sale_price": 12000,
    }, headers=h)

    r = await client.get("/api/v1/products/barcode/8934588000123", headers=h)
    assert r.status_code == 200
    assert r.json()["barcode"] == "8934588000123"


@pytest.mark.asyncio
async def test_get_by_barcode_not_found(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.get("/api/v1/products/barcode/9999999999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_product_tenant_isolation(client):
    rA = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "owner_name": "Owner A",
        "phone": "0911111111", "password": "secret123",
    })
    assert rA.status_code == 201, rA.text
    rB = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "owner_name": "Owner B",
        "phone": "0922222222", "password": "secret123",
    })
    assert rB.status_code == 201, rB.text
    tokA = rA.json()["access_token"]
    tokB = rB.json()["access_token"]

    pA = (await client.post("/api/v1/products", json={
        "name": "Item A", "sku": "SAME-SKU", "sale_price": 1000,
    }, headers=_auth(tokA))).json()

    # B can use same SKU because tenant-scoped
    r = await client.post("/api/v1/products", json={
        "name": "Item B", "sku": "SAME-SKU", "sale_price": 1000,
    }, headers=_auth(tokB))
    assert r.status_code == 201

    # B cannot see A's product
    r2 = await client.get(f"/api/v1/products/{pA['id']}", headers=_auth(tokB))
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_product_requires_auth(client):
    r = await client.get("/api/v1/products")
    assert r.status_code == 401

    r2 = await client.post("/api/v1/products", json={"name": "X", "sale_price": 1})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_auto_sku_sequential(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post(
        "/api/v1/products", json={"name": "A", "sale_price": 1000}, headers=h
    )).json()
    p2 = (await client.post(
        "/api/v1/products", json={"name": "B", "sale_price": 1000}, headers=h
    )).json()
    assert p1["sku"] != p2["sku"]
    assert p1["sku"].startswith("SP")
    assert p2["sku"].startswith("SP")


@pytest.mark.asyncio
async def test_list_products_stock_status_low(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Sắp Hết", "sale_price": 10000, "min_stock": 5,
    }, headers=h)).json()
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC Test"}, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [{"product_id": p["id"], "quantity": 3, "cost_price": 5000}],
    }, headers=h)).json()
    complete = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert complete.status_code == 200, complete.text

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] == "LOW"


@pytest.mark.asyncio
async def test_list_products_stock_status_out_never_stocked(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Chưa Nhập", "sale_price": 10000, "min_stock": 5,
    }, headers=h)).json()

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] == "OUT"


@pytest.mark.asyncio
async def test_list_products_stock_status_none_when_min_stock_zero(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Không Ngưỡng", "sale_price": 10000,
    }, headers=h)).json()

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] is None


@pytest.mark.asyncio
async def test_list_products_stock_status_none_when_sufficient(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post("/api/v1/products", json={
        "name": "SP Đủ Hàng", "sale_price": 10000, "min_stock": 5,
    }, headers=h)).json()
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC Test"}, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [{"product_id": p["id"], "quantity": 100, "cost_price": 5000}],
    }, headers=h)).json()
    complete = await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    assert complete.status_code == 200, complete.text

    resp = await client.get("/api/v1/products", headers=h)
    item = next(i for i in resp.json()["items"] if i["id"] == p["id"])
    assert item["stock_status"] is None
