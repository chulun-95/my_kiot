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
