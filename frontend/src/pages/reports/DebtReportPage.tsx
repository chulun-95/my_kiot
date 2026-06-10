import { useCallback, useEffect, useState } from 'react';
import * as reportApi from '../../api/report';
import type { DebtItem } from '../../api/report';
import * as cashApi from '../../api/cashbook';
import { formatVND } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';
import EmptyState from '../../components/EmptyState';
import { SkeletonCard } from '../../components/Skeleton';
import MoneyInput from '../../components/MoneyInput';

type Kind = 'CUSTOMER' | 'SUPPLIER';

function DebtTable({
  title, kind, items, onPaid,
}: { title: string; kind: Kind; items: DebtItem[]; onPaid: () => void }) {
  const [payingId, setPayingId] = useState<number | null>(null);
  const [amount, setAmount] = useState(0);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (partner: DebtItem) => {
    const amt = amount;
    if (!Number.isFinite(amt) || amt <= 0) { setErr('Số tiền phải lớn hơn 0'); return; }
    setErr(null);
    try {
      await cashApi.createCash({
        direction: kind === 'CUSTOMER' ? 'IN' : 'OUT',
        method: 'CASH',
        category: kind === 'CUSTOMER' ? 'DEBT_COLLECTION' : 'DEBT_PAYMENT',
        amount: amt,
        partner_type: kind,
        partner_id: partner.partner_id,
        partner_name: partner.partner_name,
      });
      setPayingId(null); setAmount(0);
      onPaid();
    } catch (e) { setErr(toFriendlyMessage(e)); }
  };

  const label = kind === 'CUSTOMER' ? 'Thu nợ' : 'Trả nợ';
  return (
    <div className="space-y-2">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="bg-white border border-slate-200 rounded overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600"><tr>
            <th className="px-3 py-2 text-left">Đối tác</th>
            <th className="px-3 py-2 text-left">SĐT</th>
            <th className="px-3 py-2 text-right">Còn nợ</th>
            <th className="px-3 py-2"></th>
          </tr></thead>
          <tbody>
            {items.length === 0 ? (
              <tr><td colSpan={4} className="px-3 py-6"><EmptyState title="Không có công nợ" /></td></tr>
            ) : items.map((it) => (
              <tr key={it.partner_id} className="border-t border-slate-100">
                <td className="px-3 py-2">{it.partner_name}</td>
                <td className="px-3 py-2">{it.phone ?? ''}</td>
                <td className="px-3 py-2 text-right font-medium">{formatVND(it.debt)}</td>
                <td className="px-3 py-2 text-right">
                  {payingId === it.partner_id ? (
                    <span className="inline-flex items-center gap-1">
                      <span className="inline-block w-32">
                        <MoneyInput value={amount} onChange={setAmount}
                          aria-label={`Số tiền ${label}`}
                          className="w-full px-2 py-1 border border-slate-300 rounded text-right" />
                      </span>
                      <button onClick={() => submit(it)} className="px-2 py-1 rounded bg-slate-900 text-white text-xs">Lưu</button>
                      <button onClick={() => { setPayingId(null); setErr(null); }} className="px-2 py-1 rounded border text-xs">Hủy</button>
                    </span>
                  ) : (
                    <button onClick={() => { setPayingId(it.partner_id); setAmount(0); }}
                      className="px-2 py-1 rounded border border-slate-300 text-xs">{label}</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {err && <div role="alert" className="text-sm text-rose-600">{err}</div>}
    </div>
  );
}

export default function DebtReportPage() {
  const [cus, setCus] = useState<DebtItem[]>([]);
  const [sup, setSup] = useState<DebtItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [c, s] = await Promise.all([reportApi.getCustomerDebts(), reportApi.getSupplierDebts()]);
      setCus(c.items); setSup(s.items);
    } catch (e) { setError(toFriendlyMessage(e)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Báo cáo công nợ</h1>
      {error && <div role="alert" className="text-sm text-rose-600">{error}</div>}
      {loading ? <SkeletonCard /> : (
        <>
          <DebtTable title="Khách hàng còn nợ (phải thu)" kind="CUSTOMER" items={cus} onPaid={load} />
          <DebtTable title="Nợ nhà cung cấp (phải trả)" kind="SUPPLIER" items={sup} onPaid={load} />
        </>
      )}
    </div>
  );
}
