import pytest

pytestmark = pytest.mark.asyncio


async def _register(client):
    payload = {
        "shop_name": "Tap Hoa Mobile",
        "owner_name": "Owner Mobile",
        "phone": "0907654321",
        "password": "secret123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return payload


async def test_mobile_login_returns_refresh_token_in_body(client):
    creds = await _register(client)
    resp = await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": creds["password"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]            # body, NOT cookie
    assert data["user"]["role"] == "OWNER"
    assert data["tenant"]["id"]
    # mobile endpoint must NOT set the web refresh cookie
    assert resp.cookies.get("refresh_token") is None


async def test_mobile_login_wrong_password_401(client):
    creds = await _register(client)
    resp = await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": "wrong-pass"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_mobile_refresh_rotates_and_returns_new_token(client):
    creds = await _register(client)
    login = (await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": creds["password"]},
    )).json()
    old_refresh = login["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/mobile/refresh", json={"refresh_token": old_refresh}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"] and data["refresh_token"] != old_refresh

    # old token is now invalid (rotation deletes it)
    reuse = await client.post(
        "/api/v1/auth/mobile/refresh", json={"refresh_token": old_refresh}
    )
    assert reuse.status_code == 401


async def test_mobile_refresh_invalid_token_401(client):
    resp = await client.post(
        "/api/v1/auth/mobile/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_mobile_logout_revokes_refresh_token(client):
    creds = await _register(client)
    login = (await client.post(
        "/api/v1/auth/mobile/login",
        json={"phone": creds["phone"], "password": creds["password"]},
    )).json()

    resp = await client.post(
        "/api/v1/auth/mobile/logout",
        json={"refresh_token": login["refresh_token"]},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert resp.status_code == 200

    # refresh with the logged-out token must fail
    after = await client.post(
        "/api/v1/auth/mobile/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert after.status_code == 401


async def test_mobile_logout_requires_auth(client):
    resp = await client.post(
        "/api/v1/auth/mobile/logout", json={"refresh_token": "x"}
    )
    assert resp.status_code == 401
