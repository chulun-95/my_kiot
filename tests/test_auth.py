from datetime import datetime, timezone

import jwt
import pytest

from backend.config import settings
from backend.shared.dates import add_months


# ---------- Register ----------

@pytest.mark.asyncio
async def test_register_success(client):
    payload = {
        "shop_name": "Tap Hoa Minh Anh",
        "phone": "0901234567",
        "address": "123 Đường ABC, Quận 1, TP.HCM",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert resp.cookies.get("refresh_token")
    assert data["tenant"]["name"] == payload["shop_name"]
    assert data["tenant"]["slug"].startswith("tap-hoa-minh-anh")
    assert data["user"]["role"] == "OWNER"
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_phone(client):
    payload = {
        "shop_name": "Shop A",
        "phone": "0901111111",
        "address": "1 Đường A, Quận 1",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    payload2 = {**payload, "shop_name": "Shop B"}
    r2 = await client.post("/api/v1/auth/register", json=payload2)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "PHONE_EXISTS"


@pytest.mark.asyncio
async def test_register_invalid_phone(client):
    payload = {
        "shop_name": "Shop X",
        "phone": "1234567",
        "address": "1 Đường X, Quận 1",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client):
    payload = {
        "shop_name": "Shop X",
        "phone": "0901234567",
        "address": "1 Đường X, Quận 1",
        "password": "123",
        "confirm_password": "123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_shop_name(client):
    payload = {
        "shop_name": "",
        "phone": "0901234567",
        "address": "1 Đường X, Quận 1",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_password_mismatch(client):
    payload = {
        "shop_name": "Shop Mismatch",
        "phone": "0903333333",
        "address": "1 Đường Mismatch, Quận 1",
        "password": "secret123",
        "confirm_password": "different456",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_sets_expiry(client):
    payload = {
        "shop_name": "Shop Expiry",
        "phone": "0904444444",
        "address": "1 Đường Expiry, Quận 1",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    before = datetime.now(tz=timezone.utc)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()

    expires_at_raw = data["tenant"]["expires_at"]
    assert expires_at_raw is not None
    expires_at = datetime.fromisoformat(expires_at_raw)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    expected = add_months(before, 6)
    assert abs((expires_at - expected).total_seconds()) < 60


@pytest.mark.asyncio
async def test_register_slug_collision_gets_suffix(client):
    p1 = {
        "shop_name": "Tap Hoa",
        "phone": "0901111111",
        "address": "1 Đường U1, Quận 1",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    p2 = {
        "shop_name": "Tap Hoa",
        "phone": "0902222222",
        "address": "2 Đường U2, Quận 1",
        "password": "secret123",
        "confirm_password": "secret123",
    }
    r1 = await client.post("/api/v1/auth/register", json=p1)
    r2 = await client.post("/api/v1/auth/register", json=p2)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["tenant"]["slug"] != r2.json()["tenant"]["slug"]
    assert r2.json()["tenant"]["slug"].startswith("tap-hoa-")


# ---------- Login ----------

@pytest.mark.asyncio
async def test_login_success(client, registered_owner):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"phone": registered_owner["phone"], "password": registered_owner["password"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" not in data
    assert resp.cookies.get("refresh_token")
    assert data["user"]["role"] == "OWNER"


@pytest.mark.asyncio
async def test_login_unknown_phone(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0909999999", "password": "anything"},
    )
    assert resp.status_code == 401
    assert "không đúng" in resp.json()["error"]["message"].lower() or \
           "khong dung" in resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_wrong_password_same_message_as_unknown(client, registered_owner):
    r_unknown = await client.post(
        "/api/v1/auth/login",
        json={"phone": "0909999999", "password": "wrong"},
    )
    r_wrong = await client.post(
        "/api/v1/auth/login",
        json={"phone": registered_owner["phone"], "password": "wrong"},
    )
    assert r_unknown.status_code == 401
    assert r_wrong.status_code == 401
    assert r_unknown.json()["error"]["message"] == r_wrong.json()["error"]["message"]


@pytest.mark.asyncio
async def test_login_jwt_payload(client, registered_owner):
    token = registered_owner["access_token"]
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    assert "sub" in payload
    assert "tid" in payload
    assert payload["role"] == "OWNER"
    assert "exp" in payload and "iat" in payload


# ---------- Logout ----------

@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(client, registered_owner):
    old = registered_owner["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {registered_owner['access_token']}"},
    )
    assert resp.status_code == 200

    r = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old})
    assert r.status_code == 401


# ---------- Refresh ----------

@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client, registered_owner):
    old_refresh = registered_owner["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert r.status_code == 200
    new_refresh = r.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh
    assert "refresh_token" not in r.json()

    # tái sử dụng token cũ → bị từ chối (reuse detection)
    r2 = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert r2.status_code == 401


# ---------- Change password ----------

@pytest.mark.asyncio
async def test_change_password_success(client, registered_owner):
    headers = {"Authorization": f"Bearer {registered_owner['access_token']}"}
    resp = await client.put(
        "/api/v1/auth/change-password",
        json={
            "current_password": registered_owner["password"],
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_change_password_wrong_current(client, registered_owner):
    headers = {"Authorization": f"Bearer {registered_owner['access_token']}"}
    resp = await client.put(
        "/api/v1/auth/change-password",
        json={
            "current_password": "wrong",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_same_as_current(client, registered_owner):
    headers = {"Authorization": f"Bearer {registered_owner['access_token']}"}
    resp = await client.put(
        "/api/v1/auth/change-password",
        json={
            "current_password": registered_owner["password"],
            "new_password": registered_owner["password"],
            "confirm_password": registered_owner["password"],
        },
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_confirm_mismatch(client, registered_owner):
    headers = {"Authorization": f"Bearer {registered_owner['access_token']}"}
    resp = await client.put(
        "/api/v1/auth/change-password",
        json={
            "current_password": registered_owner["password"],
            "new_password": "newpass123",
            "confirm_password": "different456",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_change_password_invalidates_old_refresh_tokens(client, registered_owner):
    old_refresh = registered_owner["refresh_token"]
    headers = {"Authorization": f"Bearer {registered_owner['access_token']}"}
    r = await client.put(
        "/api/v1/auth/change-password",
        json={
            "current_password": registered_owner["password"],
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
        headers=headers,
    )
    assert r.status_code == 200
    assert "refresh_token" not in r.json()

    r2 = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
    assert r2.status_code == 401


# ---------- /me ----------

@pytest.mark.asyncio
async def test_me_returns_user_and_tenant(client, registered_owner):
    headers = {"Authorization": f"Bearer {registered_owner['access_token']}"}
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "OWNER"
    assert body["tenant"]["name"]
