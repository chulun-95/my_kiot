import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_category_root(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post(
        "/api/v1/categories",
        json={"name": "Đồ uống"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Đồ uống"
    assert body["depth"] == 1
    assert body["parent_id"] is None


@pytest.mark.asyncio
async def test_create_category_child(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    parent = (await client.post(
        "/api/v1/categories", json={"name": "Đồ uống"}, headers=h
    )).json()

    r = await client.post(
        "/api/v1/categories",
        json={"name": "Nước ngọt", "parent_id": parent["id"]},
        headers=h,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["depth"] == 2
    assert body["parent_id"] == parent["id"]


@pytest.mark.asyncio
async def test_create_category_grandchild_rejected(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post(
        "/api/v1/categories", json={"name": "L1"}, headers=h
    )).json()
    p2 = (await client.post(
        "/api/v1/categories", json={"name": "L2", "parent_id": p1["id"]}, headers=h
    )).json()

    r = await client.post(
        "/api/v1/categories",
        json={"name": "L3", "parent_id": p2["id"]},
        headers=h,
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "CATEGORY_DEPTH_EXCEEDED"


@pytest.mark.asyncio
async def test_create_category_with_invalid_parent(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    r = await client.post(
        "/api/v1/categories",
        json={"name": "X", "parent_id": 99999},
        headers=h,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_categories_returns_tree(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/categories", json={"name": "Đồ uống Riêng"}, headers=h
    )).json()
    await client.post(
        "/api/v1/categories",
        json={"name": "Nước ngọt", "parent_id": p["id"]},
        headers=h,
    )
    await client.post(
        "/api/v1/categories",
        json={"name": "Cà phê", "parent_id": p["id"]},
        headers=h,
    )

    r = await client.get("/api/v1/categories", headers=h)
    assert r.status_code == 200
    body = r.json()
    root = next(n for n in body["items"] if n["id"] == p["id"])
    assert root["name"] == "Đồ uống Riêng"
    assert len(root["children"]) == 2
    child_names = {c["name"] for c in root["children"]}
    assert child_names == {"Nước ngọt", "Cà phê"}


@pytest.mark.asyncio
async def test_update_category_name(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    c = (await client.post(
        "/api/v1/categories", json={"name": "Old"}, headers=h
    )).json()
    r = await client.put(
        f"/api/v1/categories/{c['id']}",
        json={"name": "New", "sort_order": 5},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New"
    assert r.json()["sort_order"] == 5


@pytest.mark.asyncio
async def test_delete_category_empty(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    c = (await client.post(
        "/api/v1/categories", json={"name": "ToDelete"}, headers=h
    )).json()
    r = await client.delete(f"/api/v1/categories/{c['id']}", headers=h)
    assert r.status_code == 200

    # No longer in list
    r2 = await client.get("/api/v1/categories", headers=h)
    assert not any(x["id"] == c["id"] for x in r2.json()["items"])


@pytest.mark.asyncio
async def test_delete_category_with_child_blocked(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    p = (await client.post(
        "/api/v1/categories", json={"name": "Parent"}, headers=h
    )).json()
    await client.post(
        "/api/v1/categories",
        json={"name": "Child", "parent_id": p["id"]},
        headers=h,
    )
    r = await client.delete(f"/api/v1/categories/{p['id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CATEGORY_HAS_CHILDREN"


@pytest.mark.asyncio
async def test_delete_category_with_products_blocked(client, registered_owner):
    h = _auth(registered_owner["access_token"])
    cat = (await client.post(
        "/api/v1/categories", json={"name": "C"}, headers=h
    )).json()
    await client.post(
        "/api/v1/products",
        json={"name": "P1", "category_id": cat["id"], "sale_price": 1000},
        headers=h,
    )
    r = await client.delete(f"/api/v1/categories/{cat['id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CATEGORY_HAS_PRODUCTS"


@pytest.mark.asyncio
async def test_category_tenant_isolation(client):
    """Tenant A không được thấy/sửa/xóa nhóm hàng của tenant B."""
    rA = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "address": "1 Đường A, Quận 1",
        "phone": "0911111111", "password": "secret123", "confirm_password": "secret123",
    })
    assert rA.status_code == 201, rA.text
    rB = await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "address": "2 Đường B, Quận 1",
        "phone": "0922222222", "password": "secret123", "confirm_password": "secret123",
    })
    assert rB.status_code == 201, rB.text
    tokA = rA.json()["access_token"]
    tokB = rB.json()["access_token"]

    cat = (await client.post(
        "/api/v1/categories", json={"name": "OfA"}, headers=_auth(tokA)
    )).json()

    # B cannot see A's category in tree
    lst = await client.get("/api/v1/categories", headers=_auth(tokB))
    assert all(x["id"] != cat["id"] for x in lst.json()["items"])

    # B cannot delete A's category
    r = await client.delete(f"/api/v1/categories/{cat['id']}", headers=_auth(tokB))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_category_requires_auth(client):
    r = await client.get("/api/v1/categories")
    assert r.status_code == 401
