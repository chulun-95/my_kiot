import { useCallback, useEffect, useState } from 'react';
import * as staffApi from '../../api/staff';
import type { Pagination, StaffResponse } from '../../api/staff';
import StaffForm from './StaffForm';
import { toFriendlyMessage } from '../../utils/errors';

export default function StaffList() {
  const [items, setItems] = useState<StaffResponse[]>([]);
  const [pagination, setPagination] = useState<Pagination>({
    page: 1,
    limit: 20,
    total: 0,
    total_pages: 0,
  });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modal, setModal] = useState<
    { mode: 'create' } | { mode: 'edit'; staff: StaffResponse } | null
  >(null);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await staffApi.listStaff({
        page,
        limit: 20,
        search: search || undefined,
      });
      setItems(res.items);
      setPagination(res.pagination);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    const handle = setTimeout(load, 300);
    return () => clearTimeout(handle);
  }, [load]);

  const handleDeactivate = async (staff: StaffResponse) => {
    if (!confirm(`Khóa tài khoản ${staff.full_name}?`)) return;
    try {
      await staffApi.deactivateStaff(staff.id);
      load();
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  const handleActivate = async (staff: StaffResponse) => {
    try {
      await staffApi.activateStaff(staff.id);
      load();
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Nhân viên</h1>
        <button
          onClick={() => setModal({ mode: 'create' })}
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          Thêm nhân viên
        </button>
      </div>

      <input
        type="search"
        placeholder="Tìm theo tên hoặc SĐT..."
        value={search}
        onChange={(e) => {
          setPage(1);
          setSearch(e.target.value);
        }}
        className="w-full max-w-sm px-3 py-2 border border-slate-300 rounded"
      />

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 text-left">Họ tên</th>
              <th className="px-3 py-2 text-left">SĐT</th>
              <th className="px-3 py-2 text-left">Email</th>
              <th className="px-3 py-2 text-left">Vai trò</th>
              <th className="px-3 py-2 text-left">Trạng thái</th>
              <th className="px-3 py-2 text-right">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Đang tải...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-slate-500">
                  Chưa có nhân viên
                </td>
              </tr>
            ) : (
              items.map((s) => (
                <tr key={s.id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{s.full_name}</td>
                  <td className="px-3 py-2">{s.phone ?? '-'}</td>
                  <td className="px-3 py-2">{s.email ?? '-'}</td>
                  <td className="px-3 py-2">{s.role}</td>
                  <td className="px-3 py-2">
                    {s.is_active ? (
                      <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
                        Đang hoạt động
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                        Đã khóa
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right space-x-2">
                    <button
                      onClick={() => setModal({ mode: 'edit', staff: s })}
                      className="px-2 py-1 rounded border border-slate-300"
                    >
                      Sửa
                    </button>
                    {s.is_active ? (
                      <button
                        onClick={() => handleDeactivate(s)}
                        className="px-2 py-1 rounded border border-rose-300 text-rose-700"
                      >
                        Khóa
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivate(s)}
                        className="px-2 py-1 rounded border border-emerald-300 text-emerald-700"
                      >
                        Mở khóa
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">
          Trang {pagination.page} / {Math.max(1, pagination.total_pages)} —{' '}
          {pagination.total} nhân viên
        </span>
        <div className="space-x-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Trước
          </button>
          <button
            disabled={page >= pagination.total_pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-2 py-1 rounded border border-slate-300 disabled:opacity-50"
          >
            Sau
          </button>
        </div>
      </div>

      {modal && (
        <StaffForm
          mode={modal.mode}
          initial={modal.mode === 'edit' ? modal.staff : undefined}
          onClose={() => setModal(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
