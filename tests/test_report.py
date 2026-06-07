from datetime import date, datetime, timezone, timedelta

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def shop(client, registered_owner):
    """Owner + 2 sản phẩm + hàng nhập + 1 invoice COMPLETED."""
    h = _auth(registered_owner["access_token"])
    p1 = (await client.post("/api/v1/products", json={
        "name": "Coca", "sku": "COC", "sale_price": 12000, "cost_price": 9000,
        "min_stock": 5,
    }, headers=h)).json()
    p2 = (await client.post("/api/v1/products", json={
        "name": "Pepsi", "sku": "PEP", "sale_price": 25000, "cost_price": 20000,
    }, headers=h)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [
            {"product_id": p1["id"], "quantity": 100, "cost_price": 9000},
            {"product_id": p2["id"], "quantity": 50, "cost_price": 20000},
        ],
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)

    return {"headers": h, "p1": p1, "p2": p2, "token": registered_owner["access_token"]}


async def _complete_invoice(client, headers, product_id, quantity):
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": product_id, "quantity": quantity}],
    }, headers=headers)).json()
    return (await client.post(
        f"/api/v1/invoices/{inv['id']}/complete",
        json={"payments": [{"method": "CASH", "amount": float(inv["total"])}]},
        headers=headers,
    )).json()


# ===================================================================
# Dashboard
# ===================================================================

@pytest.mark.asyncio
async def test_dashboard_empty(client, shop):
    r = await client.get("/api/v1/reports/dashboard", headers=shop["headers"])
    assert r.status_code == 200
    body = r.json()
    assert float(body["today_revenue"]) == 0
    assert body["today_invoices"] == 0
    assert float(body["today_profit"]) == 0
    assert body["pending_drafts"] == 0
    # Có hàng nhập 100*9000 + 50*20000 = 1,900,000
    assert float(body["inventory_value"]) == 100 * 9000 + 50 * 20000


@pytest.mark.asyncio
async def test_dashboard_after_sale(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 3)
    await _complete_invoice(client, h, shop["p2"]["id"], 1)

    r = await client.get("/api/v1/reports/dashboard", headers=h)
    body = r.json()
    assert float(body["today_revenue"]) == 3 * 12000 + 1 * 25000
    assert body["today_invoices"] == 2
    expected_profit = (3 * 12000 + 1 * 25000) - (3 * 9000 + 1 * 20000)
    assert float(body["today_profit"]) == expected_profit


@pytest.mark.asyncio
async def test_dashboard_low_stock(client, shop):
    h = shop["headers"]
    # p1 có min_stock=5, ban đầu 100. Bán 96 → tồn 4 (<5)
    await _complete_invoice(client, h, shop["p1"]["id"], 96)

    r = await client.get("/api/v1/reports/dashboard", headers=h)
    body = r.json()
    assert body["low_stock_count"] >= 1
    # tồn còn 4 > 0 → vẫn thuộc LOW, không tính OUT_OF_STOCK
    assert "out_of_stock_count" in body
    assert body["out_of_stock_count"] == 0


@pytest.mark.asyncio
async def test_dashboard_out_of_stock(client, shop):
    h = shop["headers"]
    # Bán hết toàn bộ tồn p1 → tồn = 0 → OUT_OF_STOCK
    await _complete_invoice(client, h, shop["p1"]["id"], 100)

    r = await client.get("/api/v1/reports/dashboard", headers=h)
    body = r.json()
    assert body["out_of_stock_count"] >= 1
    assert body["low_stock_count"] >= body["out_of_stock_count"]


@pytest.mark.asyncio
async def test_dashboard_never_stocked_counts_out_of_stock(client, registered_owner):
    # SP có min_stock>0 nhưng CHƯA từng nhập kho (không có dòng inventory)
    # vẫn phải tính là hết hàng trên dashboard.
    h = _auth(registered_owner["access_token"])
    await client.post("/api/v1/products", json={
        "name": "Chưa nhập", "sale_price": 1000, "min_stock": 5,
    }, headers=h)
    r = await client.get("/api/v1/reports/dashboard", headers=h)
    body = r.json()
    assert body["out_of_stock_count"] >= 1
    assert body["low_stock_count"] >= 1


@pytest.mark.asyncio
async def test_dashboard_pending_drafts(client, shop):
    h = shop["headers"]
    await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 1}],
    }, headers=h)
    await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p2"]["id"], "quantity": 1}],
    }, headers=h)

    r = await client.get("/api/v1/reports/dashboard", headers=h)
    body = r.json()
    assert body["pending_drafts"] == 2


@pytest.mark.asyncio
async def test_dashboard_owner_only(client, shop, registered_owner):
    # Tạo cashier
    staff = await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0911999888", "password": "secret123",
    }, headers=shop["headers"])
    assert staff.status_code == 201
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0911999888", "password": "secret123",
    })).json()["access_token"]

    r = await client.get(
        "/api/v1/reports/dashboard", headers=_auth(cashier_token)
    )
    assert r.status_code == 403


# ===================================================================
# Revenue
# ===================================================================

@pytest.mark.asyncio
async def test_revenue_day_group(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 2)
    await _complete_invoice(client, h, shop["p2"]["id"], 1)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/revenue?from={today}&to={today}&group_by=day",
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["from_date"] == today
    assert body["to_date"] == today
    assert body["group_by"] == "day"
    assert body["total_invoices"] == 2
    assert float(body["total_revenue"]) == 2 * 12000 + 1 * 25000
    assert len(body["series"]) >= 1


@pytest.mark.asyncio
async def test_revenue_month_group(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 1)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/revenue?from={today}&to={today}&group_by=month",
        headers=h,
    )
    body = r.json()
    assert body["group_by"] == "month"
    if body["series"]:
        # period là YYYY-MM
        assert len(body["series"][0]["period"]) == 7


@pytest.mark.asyncio
async def test_revenue_default_range(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 1)
    r = await client.get("/api/v1/reports/revenue", headers=h)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_revenue_invalid_date_range(client, shop):
    r = await client.get(
        "/api/v1/reports/revenue?from=2026-12-31&to=2026-01-01",
        headers=shop["headers"],
    )
    assert r.status_code == 400


# ===================================================================
# Top products
# ===================================================================

@pytest.mark.asyncio
async def test_top_products(client, shop):
    h = shop["headers"]
    # p1 bán 5 cái → revenue 60000
    await _complete_invoice(client, h, shop["p1"]["id"], 5)
    # p2 bán 3 cái → revenue 75000
    await _complete_invoice(client, h, shop["p2"]["id"], 3)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/top-products?from={today}&to={today}",
        headers=h,
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 2
    # p2 doanh thu cao hơn → đứng đầu
    assert items[0]["product_id"] == shop["p2"]["id"]
    assert float(items[0]["revenue"]) == 75000
    assert float(items[0]["profit"]) == 75000 - 3 * 20000


@pytest.mark.asyncio
async def test_top_products_excludes_cancelled(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)
    await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "test"}, headers=h)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/top-products?from={today}&to={today}", headers=h
    )
    items = r.json()["items"]
    # Invoice đã cancel — không tính
    assert len(items) == 0


@pytest.mark.asyncio
async def test_top_products_multi_unit(client, shop):
    h = shop["headers"]
    unit = (await client.post(
        f"/api/v1/products/{shop['p1']['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "unit_id": unit["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(
        f"/api/v1/invoices/{inv['id']}/complete",
        json={"payments": [{"method": "CASH", "amount": float(inv["total"])}]},
        headers=h,
    )

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/top-products?from={today}&to={today}", headers=h
    )
    item = r.json()["items"][0]
    # SL quy về cơ bản: 2 × 24 = 48 (trước fix là 2 → sai)
    assert float(item["quantity_sold"]) == 48
    # profit = net(2×288000) − cost(9000×2×24) = 576000 − 432000 = 144000
    assert float(item["profit"]) == 144000


# ===================================================================
# Products sold (báo cáo SP đã bán)
# ===================================================================

@pytest.mark.asyncio
async def test_products_sold_basic(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 5)   # net 60000, cost 45000
    await _complete_invoice(client, h, shop["p2"]["id"], 3)   # net 75000, cost 60000

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}", headers=h
    )
    assert r.status_code == 200
    body = r.json()
    # default sort = revenue desc → p2 (75000) đứng đầu
    items = body["items"]
    assert len(items) == 2
    assert items[0]["product_id"] == shop["p2"]["id"]
    assert float(items[0]["quantity_sold"]) == 3
    assert float(items[0]["revenue"]) == 75000
    assert float(items[0]["net_revenue"]) == 75000
    assert float(items[0]["cost"]) == 60000
    assert float(items[0]["profit"]) == 15000
    # totals
    assert float(body["totals"]["net_revenue"]) == 135000
    assert float(body["totals"]["cost"]) == 105000
    assert float(body["totals"]["profit"]) == 30000
    # pagination
    assert body["pagination"]["total"] == 2
    assert body["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_products_sold_sort_by_quantity(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 5)   # qty 5
    await _complete_invoice(client, h, shop["p2"]["id"], 3)   # qty 3

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}"
        f"&sort_by=quantity&order=desc",
        headers=h,
    )
    items = r.json()["items"]
    assert items[0]["product_id"] == shop["p1"]["id"]  # qty 5 > 3


@pytest.mark.asyncio
async def test_products_sold_pagination(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 5)
    await _complete_invoice(client, h, shop["p2"]["id"], 3)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}&page=1&limit=1",
        headers=h,
    )
    body = r.json()
    assert len(body["items"]) == 1
    assert body["pagination"]["total"] == 2
    assert body["pagination"]["total_pages"] == 2
    # totals luôn tính trên TOÀN BỘ, không bị phân trang
    assert float(body["totals"]["net_revenue"]) == 135000


@pytest.mark.asyncio
async def test_products_sold_category_filter(client, shop):
    h = shop["headers"]
    # Tạo nhóm hàng + gán p1 vào nhóm
    cat = (await client.post("/api/v1/categories", json={"name": "Nước ngọt"}, headers=h)).json()
    await client.put(
        f"/api/v1/products/{shop['p1']['id']}",
        json={"category_id": cat["id"]},
        headers=h,
    )
    await _complete_invoice(client, h, shop["p1"]["id"], 2)
    await _complete_invoice(client, h, shop["p2"]["id"], 1)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}&category_id={cat['id']}",
        headers=h,
    )
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["product_id"] == shop["p1"]["id"]


@pytest.mark.asyncio
async def test_products_sold_multi_unit_base_quantity(client, shop):
    h = shop["headers"]
    # Tạo đơn vị "thùng" rate 24 cho p1 (tồn 100 base đủ bán 2 thùng = 48)
    unit = (await client.post(
        f"/api/v1/products/{shop['p1']['id']}/units",
        json={"unit_name": "thùng", "conversion_rate": 24},
        headers=h,
    )).json()
    # Bán 2 thùng theo đơn vị này
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "unit_id": unit["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(
        f"/api/v1/invoices/{inv['id']}/complete",
        json={"payments": [{"method": "CASH", "amount": float(inv["total"])}]},
        headers=h,
    )

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}", headers=h
    )
    item = r.json()["items"][0]
    # SL quy về đơn vị cơ bản: 2 thùng × 24 = 48
    assert float(item["quantity_sold"]) == 48
    # Giá vốn = cost_price(9000) × quantity(2) × rate(24) = 432000
    assert float(item["cost"]) == 432000


@pytest.mark.asyncio
async def test_products_sold_excludes_cancelled(client, shop):
    h = shop["headers"]
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 4}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": float(inv["total"])}],
    }, headers=h)
    await client.post(f"/api/v1/invoices/{inv['id']}/cancel", json={"reason": "test"}, headers=h)

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/products-sold?from={today}&to={today}", headers=h
    )
    assert len(r.json()["items"]) == 0


@pytest.mark.asyncio
async def test_products_sold_owner_only(client, shop):
    staff = await client.post("/api/v1/staff", json={
        "full_name": "Cashier", "phone": "0911777666", "password": "secret123",
    }, headers=shop["headers"])
    assert staff.status_code == 201
    cashier_token = (await client.post("/api/v1/auth/login", json={
        "phone": "0911777666", "password": "secret123",
    })).json()["access_token"]

    r = await client.get(
        "/api/v1/reports/products-sold", headers=_auth(cashier_token)
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_products_sold_invalid_sort(client, shop):
    r = await client.get(
        "/api/v1/reports/products-sold?sort_by=bogus", headers=shop["headers"]
    )
    assert r.status_code == 422


# ===================================================================
# Profit
# ===================================================================

@pytest.mark.asyncio
async def test_profit(client, shop):
    h = shop["headers"]
    await _complete_invoice(client, h, shop["p1"]["id"], 2)  # rev 24000 / cost 18000
    await _complete_invoice(client, h, shop["p2"]["id"], 1)  # rev 25000 / cost 20000

    today = date.today().isoformat()
    r = await client.get(
        f"/api/v1/reports/profit?from={today}&to={today}", headers=h
    )
    assert r.status_code == 200
    body = r.json()
    assert float(body["total_revenue"]) == 49000
    assert float(body["total_cost"]) == 38000
    assert float(body["gross_profit"]) == 11000
    assert body["invoices"] == 2


# ===================================================================
# Stock summary
# ===================================================================

@pytest.mark.asyncio
async def test_stock_summary(client, shop):
    h = shop["headers"]
    r = await client.get("/api/v1/reports/stock-summary", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_products"] == 2
    assert body["products_in_stock"] == 2
    assert body["products_out_of_stock"] == 0
    # 100*9000 + 50*20000 = 1,900,000
    assert float(body["total_inventory_value"]) == 1_900_000


# ===================================================================
# Debt Report
# ===================================================================

@pytest.mark.asyncio
async def test_customer_debt_derived(client, shop):
    h = shop["headers"]
    cus = (await client.post("/api/v1/customers", json={"name": "Nợ A", "phone": "0905111222"}, headers=h)).json()
    # bán chịu: total 24000, trả 10000 → nợ 14000
    inv = (await client.post("/api/v1/invoices", json={
        "customer_id": cus["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 10000}], "allow_debt": True,
    }, headers=h)

    r = await client.get("/api/v1/reports/debts/customers", headers=h)
    assert r.status_code == 200
    body = r.json()
    item = next(i for i in body["items"] if i["partner_id"] == cus["id"])
    assert float(item["debt"]) == 14000

    # thu nợ 4000 → còn 10000
    await client.post("/api/v1/cash-transactions", json={
        "direction": "IN", "method": "CASH", "category": "DEBT_COLLECTION", "amount": 4000,
        "partner_type": "CUSTOMER", "partner_id": cus["id"],
    }, headers=h)
    r2 = await client.get("/api/v1/reports/debts/customers", headers=h)
    item2 = next(i for i in r2.json()["items"] if i["partner_id"] == cus["id"])
    assert float(item2["debt"]) == 10000


@pytest.mark.asyncio
async def test_customer_debt_owner_only(client, shop):
    r = await client.post("/api/v1/staff", json={
        "full_name": "CW", "phone": "0912555666", "password": "secret123",
    }, headers=shop["headers"])
    assert r.status_code == 201, f"Staff creation failed: {r.json()}"
    login_r = await client.post("/api/v1/auth/login", json={"phone": "0912555666", "password": "secret123"})
    assert login_r.status_code == 200, f"Login failed: {login_r.json()}"
    ct = login_r.json()["access_token"]
    r = await client.get("/api/v1/reports/debts/customers", headers=_auth(ct))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_supplier_debt_derived(client, shop):
    h = shop["headers"]
    sup = (await client.post("/api/v1/suppliers", json={"name": "NCC X"}, headers=h)).json()
    # nhập chịu: total 200000, trả 50000 → nợ 150000
    r = (await client.post("/api/v1/goods-receipts", json={
        "supplier_id": sup["id"],
        "items": [{"product_id": shop["p1"]["id"], "quantity": 10, "cost_price": 20000}],
        "paid_amount": 50000,
    }, headers=h)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h)
    rep = await client.get("/api/v1/reports/debts/suppliers", headers=h)
    item = next(i for i in rep.json()["items"] if i["partner_id"] == sup["id"])
    assert float(item["debt"]) == 150000


# ===================================================================
# Tenant isolation
# ===================================================================

@pytest.mark.asyncio
async def test_report_tenant_isolation(client):
    a = (await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop A", "owner_name": "OA",
        "phone": "0903000001", "password": "secret123",
    })).json()
    b = (await client.post("/api/v1/auth/register", json={
        "shop_name": "Shop B", "owner_name": "OB",
        "phone": "0903000002", "password": "secret123",
    })).json()
    h_a = _auth(a["access_token"])
    h_b = _auth(b["access_token"])

    # Shop A bán hàng
    p = (await client.post("/api/v1/products", json={
        "name": "X", "sku": "X", "sale_price": 1000, "cost_price": 500,
    }, headers=h_a)).json()
    r = (await client.post("/api/v1/goods-receipts", json={
        "items": [{"product_id": p["id"], "quantity": 10, "cost_price": 500}],
    }, headers=h_a)).json()
    await client.post(f"/api/v1/goods-receipts/{r['id']}/complete", headers=h_a)
    await _complete_invoice(client, h_a, p["id"], 1)

    # Shop B dashboard không thấy doanh thu shop A
    r_b = await client.get("/api/v1/reports/dashboard", headers=h_b)
    body = r_b.json()
    assert float(body["today_revenue"]) == 0
    assert body["today_invoices"] == 0


@pytest.mark.asyncio
async def test_report_requires_auth(client):
    r = await client.get("/api/v1/reports/dashboard")
    assert r.status_code == 401


# ===================================================================
# End-of-Day Report
# ===================================================================

@pytest.mark.asyncio
async def test_end_of_day_cash_and_sales(client, shop):
    h = shop["headers"]
    vn_today = datetime.now(tz=timezone(timedelta(hours=7))).date().isoformat()

    # bán 2 cái p1 (12000) tiền mặt → thu 24000, doanh thu 24000
    inv = (await client.post("/api/v1/invoices", json={
        "items": [{"product_id": shop["p1"]["id"], "quantity": 2}],
    }, headers=h)).json()
    await client.post(f"/api/v1/invoices/{inv['id']}/complete", json={
        "payments": [{"method": "CASH", "amount": 24000}],
    }, headers=h)
    # chi tay tiền điện 5000
    await client.post("/api/v1/cash-transactions", json={
        "direction": "OUT", "method": "CASH", "category": "OPERATING", "amount": 5000,
    }, headers=h)

    r = await client.get(f"/api/v1/reports/end-of-day?date={vn_today}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["business_date"] == vn_today
    cash = next(m for m in body["by_method"] if m["method"] == "CASH")
    assert float(cash["total_in"]) == 24000
    assert float(cash["total_out"]) == 5000
    assert float(cash["closing"]) == float(cash["opening"]) + 24000 - 5000
    assert float(body["sales_revenue"]) == 24000
    assert body["sales_invoices"] == 1


@pytest.mark.asyncio
async def test_end_of_day_owner_only(client, shop, registered_owner):
    staff_resp = await client.post("/api/v1/staff", json={
        "full_name": "Cashier2", "phone": "0912777888", "password": "secret123",
    }, headers=shop["headers"])
    assert staff_resp.status_code == 201, f"Staff creation failed: {staff_resp.json()}"
    ct_resp = await client.post("/api/v1/auth/login", json={"phone": "0912777888", "password": "secret123"})
    assert ct_resp.status_code == 200, f"Login failed: {ct_resp.json()}"
    ct = ct_resp.json()["access_token"]
    r = await client.get("/api/v1/reports/end-of-day", headers=_auth(ct))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_end_of_day_default_today(client, shop):
    r = await client.get("/api/v1/reports/end-of-day", headers=shop["headers"])
    assert r.status_code == 200
