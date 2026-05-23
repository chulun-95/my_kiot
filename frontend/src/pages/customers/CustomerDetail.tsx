import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import * as customerApi from '../../api/customer';
import type {
  CustomerOrderHistoryItem,
  CustomerResponse,
} from '../../api/customer';
import CustomerForm from './CustomerForm';
import RoleGate from '../../components/RoleGate';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function CustomerDetail() {
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = params.id ? Number(params.id) : null;
  const [customer, setCustomer] = useState<CustomerResponse | null>(null);
  const [orders, setOrders] = useState<CustomerOrderHistoryItem[]>([]);
  const [tab, setTab] = useState<'info' | 'history'>('info');
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (id == null) return;
    setLoading(true);
    setError(null);
    try {
      const res = await customerApi.getCustomer(id);
      setCustomer(res.customer);
      setOrders(res.recent_orders);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async () => {
    if (id == null) return;
    if (!confirm('Xóa khách hàng này?')) return;
    try {
      await customerApi.deleteCustomer(id);
      navigate('/customers');
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  if (loading) return <div className="p-4 text-slate-500">Đang tải...</div>;
  if (error) return <div className="p-4 text-rose-600">{error}</div>;
  if (!customer) return <div className="p-4">Không tìm thấy khách hàng</div>;

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{customer.name}</h1>
        <RoleGate allow={['OWNER']}>
          <button
            onClick={handleDelete}
            className="px-3 py-2 rounded border border-rose-300 text-rose-700"
          >
            Xóa
          </button>
        </RoleGate>
      </div>

      <div className="border-b border-slate-200 flex gap-4">
        <button
          onClick={() => setTab('info')}
          className={`pb-2 text-sm ${
            tab === 'info'
              ? 'border-b-2 border-slate-900 font-medium'
              : 'text-slate-600'
          }`}
        >
          Thông tin
        </button>
        <button
          onClick={() => setTab('history')}
          className={`pb-2 text-sm ${
            tab === 'history'
              ? 'border-b-2 border-slate-900 font-medium'
              : 'text-slate-600'
          }`}
        >
          Lịch sử mua ({orders.length})
        </button>
      </div>

      {tab === 'info' && (
        <>
          {editing ? (
            <CustomerForm
              mode="edit"
              initial={customer}
              onSaved={() => {
                setEditing(false);
                load();
              }}
              onCancel={() => setEditing(false)}
            />
          ) : (
            <div className="bg-white border border-slate-200 rounded p-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-slate-500">SĐT</div>
                <div>{customer.phone ?? '-'}</div>
              </div>
              <div>
                <div className="text-slate-500">Email</div>
                <div>{customer.email ?? '-'}</div>
              </div>
              <div className="col-span-2">
                <div className="text-slate-500">Địa chỉ</div>
                <div>{customer.address ?? '-'}</div>
              </div>
              <div>
                <div className="text-slate-500">Tổng chi tiêu</div>
                <div>{formatVND(customer.total_spent as number)}</div>
              </div>
              <div>
                <div className="text-slate-500">Số đơn</div>
                <div>{customer.total_orders}</div>
              </div>
              <div className="col-span-2">
                <div className="text-slate-500">Ghi chú</div>
                <div className="whitespace-pre-wrap">{customer.note ?? '-'}</div>
              </div>
              <div className="col-span-2 flex justify-end">
                <button
                  onClick={() => setEditing(true)}
                  className="px-3 py-2 rounded border border-slate-300"
                >
                  Sửa
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {tab === 'history' && (
        <div className="bg-white border border-slate-200 rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-3 py-2 text-left">Mã hóa đơn</th>
                <th className="px-3 py-2 text-left">Thời gian</th>
                <th className="px-3 py-2 text-right">Tổng</th>
                <th className="px-3 py-2 text-left">Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {orders.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
                    className="px-3 py-6 text-center text-slate-500"
                  >
                    Chưa có lịch sử mua
                  </td>
                </tr>
              ) : (
                orders.map((o) => (
                  <tr key={o.invoice_id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-mono">{o.code}</td>
                    <td className="px-3 py-2">
                      {o.completed_at ? formatDate(o.completed_at) : '-'}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {formatVND(o.total as number)}
                    </td>
                    <td className="px-3 py-2">{o.status}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
