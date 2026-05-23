import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import * as productApi from '../../api/product';
import * as categoryApi from '../../api/category';
import type { ProductStatus } from '../../api/product';
import type { CategoryNode } from '../../api/category';
import { useAuthStore } from '../../stores/authStore';
import { toFriendlyMessage } from '../../utils/errors';

function flattenCategories(nodes: CategoryNode[], depth = 0): Array<{ id: number; label: string }> {
  const out: Array<{ id: number; label: string }> = [];
  for (const n of nodes) {
    out.push({ id: n.id, label: `${'— '.repeat(depth)}${n.name}` });
    if (n.children?.length) out.push(...flattenCategories(n.children, depth + 1));
  }
  return out;
}

export default function ProductForm() {
  const params = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const role = useAuthStore((s) => s.user?.role);
  const isOwner = role === 'OWNER';
  const mode: 'create' | 'edit' = params.id ? 'edit' : 'create';
  const productId = params.id ? Number(params.id) : null;

  const [name, setName] = useState('');
  const [sku, setSku] = useState('');
  const [barcode, setBarcode] = useState('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [description, setDescription] = useState('');
  const [unit, setUnit] = useState('cái');
  const [costPrice, setCostPrice] = useState<string>('0');
  const [salePrice, setSalePrice] = useState<string>('0');
  const [minStock, setMinStock] = useState<string>('0');
  const [imageUrl, setImageUrl] = useState('');
  const [status, setStatus] = useState<ProductStatus>('ACTIVE');
  const [allowNegative, setAllowNegative] = useState(false);

  const [categories, setCategories] = useState<Array<{ id: number; label: string }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await categoryApi.listCategories();
        setCategories(flattenCategories(res.items));
      } catch {
        // ignore
      }
    })();
  }, []);

  useEffect(() => {
    if (mode !== 'edit' || productId == null) return;
    setLoading(true);
    (async () => {
      try {
        const p = await productApi.getProduct(productId);
        setName(p.name);
        setSku(p.sku);
        setBarcode(p.barcode ?? '');
        setCategoryId(p.category_id ?? '');
        setDescription(p.description ?? '');
        setUnit(p.unit);
        setCostPrice(p.cost_price == null ? '' : String(p.cost_price));
        setSalePrice(String(p.sale_price));
        setMinStock(String(p.min_stock));
        setImageUrl(p.image_url ?? '');
        setStatus(p.status);
        setAllowNegative(p.allow_negative);
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [mode, productId]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const payload = {
        name,
        sku: sku.trim() || undefined,
        barcode: barcode.trim() || undefined,
        category_id: categoryId === '' ? null : categoryId,
        description: description || undefined,
        unit,
        cost_price: isOwner && costPrice !== '' ? Number(costPrice) : undefined,
        sale_price: Number(salePrice),
        min_stock: Number(minStock || '0'),
        image_url: imageUrl || undefined,
        status,
        allow_negative: allowNegative,
      };
      let savedId = productId;
      if (mode === 'create') {
        const created = await productApi.createProduct(payload);
        savedId = created.id;
      } else if (productId != null) {
        await productApi.updateProduct(productId, payload);
      }
      if (savedId != null) navigate(`/products/${savedId}`);
      else navigate('/products');
    } catch (err) {
      setError(toFriendlyMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-slate-500">Đang tải...</div>;
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">
        {mode === 'create' ? 'Thêm sản phẩm' : 'Sửa sản phẩm'}
      </h1>
      <form onSubmit={onSubmit} className="space-y-3 bg-white p-5 rounded border border-slate-200">
        <label className="block">
          <span className="text-sm text-slate-700">Tên sản phẩm *</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={1}
            maxLength={300}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-sm text-slate-700">SKU (để trống = tự sinh)</span>
            <input
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              maxLength={50}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            />
          </label>
          <label className="block">
            <span className="text-sm text-slate-700">Mã vạch</span>
            <input
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
              maxLength={50}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            />
          </label>
        </div>
        <label className="block">
          <span className="text-sm text-slate-700">Nhóm hàng</span>
          <select
            value={categoryId}
            onChange={(e) =>
              setCategoryId(e.target.value === '' ? '' : Number(e.target.value))
            }
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          >
            <option value="">Không có nhóm</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-sm text-slate-700">Mô tả</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <div className="grid grid-cols-3 gap-3">
          <label className="block">
            <span className="text-sm text-slate-700">Đơn vị</span>
            <input
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              maxLength={30}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            />
          </label>
          {isOwner && (
            <label className="block">
              <span className="text-sm text-slate-700">Giá vốn</span>
              <input
                type="number"
                min={0}
                step="0.01"
                value={costPrice}
                onChange={(e) => setCostPrice(e.target.value)}
                className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
              />
            </label>
          )}
          <label className="block">
            <span className="text-sm text-slate-700">Giá bán *</span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={salePrice}
              onChange={(e) => setSalePrice(e.target.value)}
              required
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            />
          </label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-sm text-slate-700">Tồn tối thiểu (cảnh báo)</span>
            <input
              type="number"
              min={0}
              value={minStock}
              onChange={(e) => setMinStock(e.target.value)}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            />
          </label>
          <label className="block">
            <span className="text-sm text-slate-700">Trạng thái</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as ProductStatus)}
              className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
            >
              <option value="ACTIVE">Đang bán</option>
              <option value="INACTIVE">Ngừng bán</option>
              <option value="DRAFT">Nháp</option>
            </select>
          </label>
        </div>
        <label className="block">
          <span className="text-sm text-slate-700">URL ảnh</span>
          <input
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            maxLength={500}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded"
          />
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={allowNegative}
            onChange={(e) => setAllowNegative(e.target.checked)}
          />
          <span className="text-sm text-slate-700">Cho phép bán âm tồn</span>
        </label>

        {error && (
          <div role="alert" className="text-sm text-rose-600">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={() => navigate(-1)}
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
