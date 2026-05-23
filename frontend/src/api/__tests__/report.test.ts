import { describe, it, expect } from 'vitest';
import * as reportApi from '../report';

describe('report API', () => {
  it('getDashboard returns KPIs', async () => {
    const res = await reportApi.getDashboard();
    expect(Number(res.today_revenue)).toBe(1500000);
    expect(res.today_invoices).toBe(12);
    expect(res.low_stock_count).toBe(3);
  });

  it('getRevenue forwards from/to/group_by and returns series', async () => {
    const res = await reportApi.getRevenue({
      from: '2026-05-01',
      to: '2026-05-23',
      group_by: 'day',
    });
    expect(res.from_date).toBe('2026-05-01');
    expect(res.to_date).toBe('2026-05-23');
    expect(res.group_by).toBe('day');
    expect(res.series.length).toBe(3);
    expect(Number(res.total_revenue)).toBe(3000000);
  });

  it('getTopProducts forwards range + limit', async () => {
    const res = await reportApi.getTopProducts({
      from: '2026-05-01',
      to: '2026-05-23',
      limit: 5,
    });
    expect(res.items.length).toBe(2);
    expect(res.items[0].product_sku).toBe('SP000001');
  });

  it('getProfit returns gross_profit', async () => {
    const res = await reportApi.getProfit({
      from: '2026-05-01',
      to: '2026-05-23',
    });
    expect(Number(res.gross_profit)).toBe(900000);
    expect(res.invoices).toBe(25);
  });

  it('getStockSummary returns inventory totals', async () => {
    const res = await reportApi.getStockSummary();
    expect(res.total_products).toBe(50);
    expect(res.products_in_stock).toBe(45);
    expect(Number(res.total_inventory_value)).toBe(25000000);
  });
});
