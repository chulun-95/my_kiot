import pytest


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_staff(client, owner_token, phone="0987654321", password="staff123"):
    return await client.post(
        "/api/v1/staff",
        json={
            "full_name": "Staff One",
            "phone": phone,
            "password": password,
        },
        headers=auth(owner_token),
    )


@pytest.mark.asyncio
async def test_owner_creates_staff(client, registered_owner):
    r = await _create_staff(client, registered_owner["access_token"])
    assert r.status_code == 201
    data = r.json()
    assert data["role"] == "CASHIER"
    assert data["is_active"] is True
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_cashier_cannot_create_staff(client, registered_owner):
    # First, owner creates a CASHIER
    await _create_staff(client, registered_owner["access_token"], phone="0987654321")

    # Cashier logs in
    login = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0987654321", "password": "staff123"},
    )
    assert login.status_code == 200
    cashier_token = login.json()["access_token"]

    # Cashier tries to create another staff
    r = await client.post(
        "/api/v1/staff",
        json={"full_name": "X", "phone": "0986666666", "password": "secret123"},
        headers=auth(cashier_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_staff_duplicate_phone_in_tenant(client, registered_owner):
    r1 = await _create_staff(client, registered_owner["access_token"], phone="0987654321")
    assert r1.status_code == 201
    r2 = await _create_staff(client, registered_owner["access_token"], phone="0987654321")
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_new_staff_can_login(client, registered_owner):
    r = await _create_staff(client, registered_owner["access_token"])
    assert r.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0987654321", "password": "staff123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "CASHIER"


@pytest.mark.asyncio
async def test_deactivate_staff_blocks_login(client, registered_owner):
    create = await _create_staff(client, registered_owner["access_token"])
    staff_id = create.json()["id"]

    r = await client.patch(
        f"/api/v1/staff/{staff_id}/deactivate",
        headers=auth(registered_owner["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    login = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0987654321", "password": "staff123"},
    )
    assert login.status_code == 403


@pytest.mark.asyncio
async def test_owner_cannot_deactivate_self(client, registered_owner):
    own_id = registered_owner["user"]["id"]
    r = await client.patch(
        f"/api/v1/staff/{own_id}/deactivate",
        headers=auth(registered_owner["access_token"]),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_cashier_cannot_deactivate_others(client, registered_owner):
    # Two cashiers
    c1 = await _create_staff(client, registered_owner["access_token"], phone="0987654321")
    c2 = await _create_staff(client, registered_owner["access_token"], phone="0987111222")
    assert c2.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0987654321", "password": "staff123"},
    )
    cashier_token = login.json()["access_token"]

    r = await client.patch(
        f"/api/v1/staff/{c2.json()['id']}/deactivate",
        headers=auth(cashier_token),
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_activate_staff_allows_login(client, registered_owner):
    create = await _create_staff(client, registered_owner["access_token"])
    staff_id = create.json()["id"]

    await client.patch(
        f"/api/v1/staff/{staff_id}/deactivate",
        headers=auth(registered_owner["access_token"]),
    )
    r = await client.patch(
        f"/api/v1/staff/{staff_id}/activate",
        headers=auth(registered_owner["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is True

    login = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0987654321", "password": "staff123"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_list_staff_pagination(client, registered_owner):
    for i in range(3):
        await _create_staff(
            client,
            registered_owner["access_token"],
            phone=f"098000000{i}",
        )
    r = await client.get(
        "/api/v1/staff?page=1&limit=10",
        headers=auth(registered_owner["access_token"]),
    )
    assert r.status_code == 200
    body = r.json()
    # 3 cashiers + 1 owner = 4 users in tenant
    assert body["pagination"]["total"] == 4
    assert len(body["items"]) == 4
    for item in body["items"]:
        assert "password_hash" not in item
