import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def owner_h(registered_owner):
    return _auth(registered_owner["access_token"])


@pytest.mark.asyncio
async def test_create_manual_receipt_and_balance(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "CAPITAL",
        "amount": 500000, "note": "Góp vốn",
    }, headers=owner_h)
    assert r.status_code == 201
    body = r.json()
    assert body["code"].startswith("PT")
    assert body["direction"] == "IN"
    assert body["ref_type"] == "MANUAL"

    lst = await client.get("/api/v1/cash-transactions", headers=owner_h)
    assert lst.status_code == 200
    data = lst.json()
    assert float(data["summary"]["balance_total"]) == 500000
    assert float(data["summary"]["range_in"]) == 500000
    by_cash = next(m for m in data["summary"]["balance_by_method"] if m["method"] == "CASH")
    assert float(by_cash["balance"]) == 500000


@pytest.mark.asyncio
async def test_create_manual_payment_code_pc(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "SALARY", "amount": 200000,
    }, headers=owner_h)
    assert r.status_code == 201
    assert r.json()["code"].startswith("PC")


@pytest.mark.asyncio
async def test_manual_rejects_auto_only_category(client, owner_h):
    r = await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "SALE", "amount": 1000,
    }, headers=owner_h)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_CASH_CATEGORY"


@pytest.mark.asyncio
async def test_cancel_manual_excluded_from_balance(client, owner_h):
    created = (await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "OTHER_IN", "amount": 300000,
    }, headers=owner_h)).json()
    c = await client.post(
        f"/api/v1/cash-transactions/{created['id']}/cancel",
        json={"reason": "nhầm"}, headers=owner_h,
    )
    assert c.status_code == 200
    assert c.json()["status"] == "CANCELLED"

    data = (await client.get("/api/v1/cash-transactions", headers=owner_h)).json()
    assert float(data["summary"]["balance_total"]) == 0


@pytest.mark.asyncio
async def test_cashbook_owner_only(client, registered_owner):
    await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0912000111", "password": "secret123",
    }, headers=_auth(registered_owner["access_token"]))
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0912000111", "password": "secret123",
    })).json()["access_token"]
    r = await client.get("/api/v1/cash-transactions", headers=_auth(cashier_token))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cashbook_filter_by_direction(client, owner_h):
    await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "OTHER_IN", "amount": 100000,
    }, headers=owner_h)
    await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "OTHER_OUT", "amount": 40000,
    }, headers=owner_h)
    data = (await client.get(
        "/api/v1/cash-transactions?direction=OUT", headers=owner_h
    )).json()
    assert all(i["direction"] == "OUT" for i in data["items"])
    assert float(data["summary"]["balance_total"]) == 60000  # summary luôn tính toàn bộ
