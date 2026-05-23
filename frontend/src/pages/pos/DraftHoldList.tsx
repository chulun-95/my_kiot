import { useEffect, useState } from 'react';
import * as invoiceApi from '../../api/invoice';
import type { InvoiceBrief, InvoiceResponse } from '../../api/invoice';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

interface Props {
  onRestore: (invoice: InvoiceResponse) => void;
  onClose: () => void;
}

export default function DraftHoldList({ onRestore, onClose }: Props) {
  const [drafts, setDrafts] = useState<InvoiceBrief[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [restoringId, setRestoringId] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await invoiceApi.listDrafts(true);
        setDrafts(res.items);
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleRestore = async (id: number) => {
    setRestoringId(id);
    try {
      const inv = await invoiceApi.getInvoice(id);
      onRestore(inv);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setRestoringId(null);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Hóa đơn treo"
      className="fixed inset-y-0 right-0 w-96 bg-white border-l border-slate-200 shadow-lg z-40 flex flex-col"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <h2 className="text-lg font-semibold">Hóa đơn treo</h2>
        <button
          onClick={onClose}
          className="px-2 py-1 rounded border border-slate-300 text-sm"
        >
          Đóng
        </button>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {loading && <div className="text-sm text-slate-500">Đang tải...</div>}
        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}
        {!loading && drafts.length === 0 && (
          <div className="text-sm text-slate-500">Không có hóa đơn treo</div>
        )}
        {drafts.map((d) => (
          <div
            key={d.id}
            className="border border-slate-200 rounded p-3 flex flex-col gap-1"
          >
            <div className="flex justify-between items-center">
              <span className="font-mono text-sm">{d.code}</span>
              <span className="font-semibold">{formatVND(d.total)}</span>
            </div>
            <div className="text-xs text-slate-500">
              {d.customer_name ?? 'Khách lẻ'} · {formatDate(d.created_at)}
            </div>
            <button
              onClick={() => handleRestore(d.id)}
              disabled={restoringId === d.id}
              className="self-end px-2 py-1 text-sm rounded bg-slate-900 text-white disabled:opacity-50"
            >
              {restoringId === d.id ? 'Đang khôi phục...' : 'Khôi phục'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
