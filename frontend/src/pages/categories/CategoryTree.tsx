import { useCallback, useEffect, useState, type FormEvent } from 'react';
import * as categoryApi from '../../api/category';
import type { CategoryNode } from '../../api/category';
import { toFriendlyMessage } from '../../utils/errors';
import FieldHint from '../../components/FieldHint';

interface FormState {
  mode: 'create' | 'edit';
  parentId: number | null;
  initial?: CategoryNode;
}

function CategoryForm({
  state,
  onClose,
  onSaved,
}: {
  state: FormState;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(state.initial?.name ?? '');
  const [sortOrder, setSortOrder] = useState<string>(
    String(state.initial?.sort_order ?? 0),
  );
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (state.mode === 'create') {
        await categoryApi.createCategory({
          name,
          parent_id: state.parentId ?? undefined,
          sort_order: Number(sortOrder || '0'),
        });
      } else if (state.initial) {
        await categoryApi.updateCategory(state.initial.id, {
          name,
          sort_order: Number(sortOrder || '0'),
        });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50"
    >
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md bg-white p-5 rounded shadow space-y-3"
      >
        <h2 className="text-lg font-semibold">
          {state.mode === 'create'
            ? state.parentId
              ? 'Thêm nhóm con'
              : 'Thêm nhóm hàng'
            : 'Sửa nhóm hàng'}
        </h2>
        <label className="block">
          <span className="text-sm text-slate-700">Tên nhóm</span>
          <FieldHint text="Tên nhóm hàng để gom các SP cùng loại (ví dụ: Đồ uống, Bánh kẹo). Hiển thị trong dropdown khi tạo SP và dùng để lọc danh sách." />
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={1}
            maxLength={200}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Thứ tự hiển thị</span>
          <FieldHint text="Số nhỏ hơn xuất hiện trước. Dùng để sắp xếp thứ tự nhóm trong danh sách và trên màn POS. Để 0 nếu chưa cần ưu tiên." />
          <input
            type="number"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 rounded border border-slate-300"
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-2 rounded bg-slate-900 text-white disabled:opacity-50"
          >
            {submitting ? 'Đang lưu...' : 'Lưu'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function CategoryTree() {
  const [items, setItems] = useState<CategoryNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<FormState | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await categoryApi.listCategories();
      setItems(res.items);
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (node: CategoryNode) => {
    if (!confirm(`Xóa nhóm "${node.name}"?`)) return;
    try {
      await categoryApi.deleteCategory(node.id);
      load();
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Nhóm hàng</h1>
        <button
          onClick={() => setForm({ mode: 'create', parentId: null })}
          className="px-3 py-2 rounded bg-slate-900 text-white"
        >
          + Thêm nhóm cha
        </button>
      </div>

      {error && (
        <div role="alert" className="text-sm text-rose-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded">
        {loading && items.length === 0 ? (
          <div className="px-3 py-6 text-center text-slate-500">Đang tải...</div>
        ) : items.length === 0 ? (
          <div className="px-3 py-6 text-center text-slate-500">
            Chưa có nhóm hàng
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {items.map((parent) => (
              <li key={parent.id} className="px-3 py-2">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium">{parent.name}</span>
                    <span className="text-xs text-slate-500 ml-2">
                      (thứ tự: {parent.sort_order})
                    </span>
                  </div>
                  <div className="flex gap-2 text-sm">
                    <button
                      onClick={() =>
                        setForm({ mode: 'create', parentId: parent.id })
                      }
                      className="px-2 py-1 rounded border border-slate-300"
                    >
                      + Thêm con
                    </button>
                    <button
                      onClick={() =>
                        setForm({ mode: 'edit', parentId: null, initial: parent })
                      }
                      className="px-2 py-1 rounded border border-slate-300"
                    >
                      Sửa
                    </button>
                    <button
                      onClick={() => handleDelete(parent)}
                      className="px-2 py-1 rounded border border-rose-300 text-rose-700"
                    >
                      Xóa
                    </button>
                  </div>
                </div>
                {parent.children?.length > 0 && (
                  <ul className="mt-2 pl-6 space-y-1">
                    {parent.children.map((child) => (
                      <li
                        key={child.id}
                        className="flex items-center justify-between border-l-2 border-slate-200 pl-3 py-1"
                      >
                        <div>
                          <span>{child.name}</span>
                          <span className="text-xs text-slate-500 ml-2">
                            (thứ tự: {child.sort_order})
                          </span>
                        </div>
                        <div className="flex gap-2 text-sm">
                          <button
                            disabled
                            title="Chỉ cho phép 2 cấp"
                            className="px-2 py-1 rounded border border-slate-200 text-slate-400 cursor-not-allowed"
                          >
                            + Thêm con
                          </button>
                          <button
                            onClick={() =>
                              setForm({
                                mode: 'edit',
                                parentId: parent.id,
                                initial: child,
                              })
                            }
                            className="px-2 py-1 rounded border border-slate-300"
                          >
                            Sửa
                          </button>
                          <button
                            onClick={() => handleDelete(child)}
                            className="px-2 py-1 rounded border border-rose-300 text-rose-700"
                          >
                            Xóa
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {form && (
        <CategoryForm
          state={form}
          onClose={() => setForm(null)}
          onSaved={load}
        />
      )}
    </div>
  );
}
