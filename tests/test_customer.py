import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- Customer CRUD ----------

@pytest.mark.asyncio
async def test_create_customer(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post(
        "/api/v1/customers",
        json={"name": "Anh Tuấn", "phone": "0987654321", "note": "Khách VIP"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["name"] == "Anh Tuấn"
    assert c["phone"] == "0987654321"
    assert float(c["total_spent"]) == 0.0
    assert c["total_orders"] == 0


@pytest.mark.asyncio
async def test_create_customer_no_phone(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post(
        "/api/v1/customers",
        json={"name": "Khách vãng lai"},
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["phone"] is None


@pytest.mark.asyncio
async def test_create_customer_duplicate_phone(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    payload = {"name": "A", "phone": "0987654321"}
    r1 = await client.post("/api/v1/customers", json=payload, headers=h)
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/customers",
        json={"name": "B", "phone": "0987654321"},
        headers=h,
    )
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] in {"PHONE_EXISTS", "DUPLICATE"}


@pytest.mark.asyncio
async def test_multiple_customers_no_phone_allowed(client, registered_owner):
    """Nhiều KH không có SĐT vẫn OK (partial unique không bắt NULL)."""
    h = _auth(registered_owner["access_token"])
    r1 = await client.post("/api/v1/customers", json={"name": "K1"}, headers=h)
    r2 = await client.post("/api/v1/customers", json={"name": "K2"}, headers=h)
    assert r1.status_code == 201
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_update_customer(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    c = (await client.post(
        "/api/v1/customers",
        json={"name": "Old Name", "phone": "0987654321"},
        headers=h,
    )).json()

    r = await client.put(
        f"/api/v1/customers/{c['id']}",
        json={"name": "New Name", "address": "Hà Nội"},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "New Name"
    assert body["address"] == "Hà Nội"
    assert body["phone"] == "0987654321"  # unchanged


@pytest.mark.asyncio
async def test_update_customer_phone_collision(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    c1 = (await client.post("/api/v1/customers", json={
        "name": "A", "phone": "0987111111",
    }, headers=h)).json()
    c2 = (await client.post("/api/v1/customers", json={
        "name": "B", "phone": "0987222222",
    }, headers=h)).json()

    r = await client.put(
        f"/api/v1/customers/{c2['id']}",
        json={"phone": "0987111111"},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_list_customers_pagination(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    for i in range(15):
        await client.post(
            "/api/v1/customers",
            json={"name": f"KH{i}"},
            headers=h,
        )

    r = await client.get("/api/v1/customers?page=1&limit=10", headers=h)
    body = r.json()
    assert body["pagination"]["total"] == 15
    assert len(body["items"]) == 10


@pytest.mark.asyncio
async def test_list_customers_search_by_name(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/customers", json={
        "name": "Nguyễn Văn A", "phone": "0987000001",
    }, headers=h)
    await client.post("/api/v1/customers", json={
        "name": "Trần Văn B", "phone": "0987000002",
    }, headers=h)

    r = await client.get("/api/v1/customers?search=Nguyễn", headers=h)
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Nguyễn Văn A"


@pytest.mark.asyncio
async def test_find_customer_by_phone(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/customers", json={
        "name": "Khách 1", "phone": "0911999888",
    }, headers=h)

    r = await client.get("/api/v1/customers/phone/0911999888", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Khách 1"


@pytest.mark.asyncio
async def test_find_customer_by_phone_not_found(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.get("/api/v1/customers/phone/0000000000", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_customer_detail(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    c = (await client.post("/api/v1/customers", json={
        "name": "X", "phone": "0987000003",
    }, headers=h)).json()

    r = await client.get(f"/api/v1/customers/{c['id']}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["customer"]["name"] == "X"
    assert body["recent_orders"] == []  # no invoices yet


@pytest.mark.asyncio
async def test_delete_customer_soft(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    c = (await client.post("/api/v1/customers", json={
        "name": "ToDelete", "phone": "0987000004",
    }, headers=h)).json()

    r = await client.delete(f"/api/v1/customers/{c['id']}", headers=h)
    assert r.status_code == 200

    # Sau khi xóa, có thể tạo KH khác cùng SĐT
    r2 = await client.post("/api/v1/customers", json={
        "name": "ReUse", "phone": "0987000004",
    }, headers=h)
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_customer_tenant_isolation(client):
    rA = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "address": "1 Đường A, Quận 1",
        "phone": "0911111111", "password": "secret123", "confirm_password": "secret123",
    })
    rB = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "address": "2 Đường B, Quận 1",
        "phone": "0922222222", "password": "secret123", "confirm_password": "secret123",
    })
    tokA = rA.json()["access_token"]
    tokB = rB.json()["access_token"]

    cA = (await client.post("/api/v1/customers", json={
        "name": "KH A", "phone": "0987111111",
    }, headers=_auth(tokA))).json()

    # B không thấy KH của A
    r = await client.get(f"/api/v1/customers/{cA['id']}", headers=_auth(tokB))
    assert r.status_code == 404

    # B dùng được SĐT trùng (vì tenant-scoped)
    r2 = await client.post("/api/v1/customers", json={
        "name": "KH B", "phone": "0987111111",
    }, headers=_auth(tokB))
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_customer_requires_auth(client):
    r = await client.get("/api/v1/customers")
    assert r.status_code == 401


# ---------- Supplier ----------

@pytest.mark.asyncio
async def test_create_supplier(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post("/api/v1/suppliers", json={
        "name": "NCC Coca",
        "phone": "0241234567",
        "tax_code": "0123456789",
        "address": "KCN Sóng Thần",
    }, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "NCC Coca"
    assert body["tax_code"] == "0123456789"
    assert float(body["total_debt"]) == 0.0


@pytest.mark.asyncio
async def test_update_supplier(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    s = (await client.post("/api/v1/suppliers", json={
        "name": "Old", "phone": "0241000001",
    }, headers=h)).json()

    r = await client.put(f"/api/v1/suppliers/{s['id']}", json={
        "name": "New", "address": "Hà Nội",
    }, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "New"
    assert body["address"] == "Hà Nội"


@pytest.mark.asyncio
async def test_update_supplier_partial_does_not_wipe_omitted_fields(client, registered_owner):
    """Regression test: Android gửi JSON với explicit null cho fields không thay đổi.

    Regression: Android ngắt DTO encode với encodeDefaults=true, nên PUT request
    chứa ALL fields của SupplierUpdateRequest, với null tường minh cho các field
    form không populate. Nếu backend dùng 'else: setattr()' mà không check 'v is not None',
    sẽ wipe email/tax_code/note thành NULL.

    Test này gửi payload thực sự matching Android:
      {"name": "...", "phone": "0241999999", "email": null, "address": "...", "tax_code": null, "note": null}
    và verify rằng nulls KHÔNG wipe những giá trị cũ.
    """
    h = _auth(registered_owner["access_token"])
    s = (await client.post("/api/v1/suppliers", json={
        "name": "NCC Đầy Đủ",
        "phone": "0241000002",
        "email": "ncc@example.com",
        "address": "KCN Sóng Thần",
        "tax_code": "0987654321",
        "note": "Giao hàng thứ 2 hàng tuần",
    }, headers=h)).json()

    # PUT với explicit null cho email/tax_code/note (matching Android encodeDefaults=true behavior)
    r = await client.put(f"/api/v1/suppliers/{s['id']}", json={
        "name": "NCC Đầy Đủ",
        "phone": "0241999999",
        "email": None,
        "address": "KCN Sóng Thần",
        "tax_code": None,
        "note": None,
    }, headers=h)
    assert r.status_code == 200
    body = r.json()
    # Phone được thay đổi
    assert body["phone"] == "0241999999"
    # Các field khác KHÔNG bị wipe - giữ nguyên giá trị cũ
    assert body["email"] == "ncc@example.com", "Explicit null không được wipe email"
    assert body["tax_code"] == "0987654321", "Explicit null không được wipe tax_code"
    assert body["note"] == "Giao hàng thứ 2 hàng tuần", "Explicit null không được wipe note"
    assert body["address"] == "KCN Sóng Thần"
    assert body["name"] == "NCC Đầy Đủ"


@pytest.mark.asyncio
async def test_list_suppliers_search(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/suppliers", json={"name": "NCC A"}, headers=h)
    await client.post("/api/v1/suppliers", json={"name": "NCC B"}, headers=h)

    r = await client.get("/api/v1/suppliers?search=A", headers=h)
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "NCC A"


@pytest.mark.asyncio
async def test_delete_supplier(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    s = (await client.post("/api/v1/suppliers", json={"name": "X"}, headers=h)).json()
    r = await client.delete(f"/api/v1/suppliers/{s['id']}", headers=h)
    assert r.status_code == 200

    r2 = await client.get(f"/api/v1/suppliers/{s['id']}", headers=h)
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_supplier_tenant_isolation(client):
    rA = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "address": "1 Đường A, Quận 1",
        "phone": "0911111111", "password": "secret123", "confirm_password": "secret123",
    })
    rB = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "address": "2 Đường B, Quận 1",
        "phone": "0922222222", "password": "secret123", "confirm_password": "secret123",
    })
    tokA = rA.json()["access_token"]
    tokB = rB.json()["access_token"]

    sA = (await client.post("/api/v1/suppliers", json={
        "name": "NCC of A",
    }, headers=_auth(tokA))).json()

    r = await client.get(f"/api/v1/suppliers/{sA['id']}", headers=_auth(tokB))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_supplier_requires_auth(client):
    r = await client.get("/api/v1/suppliers")
    assert r.status_code == 401
