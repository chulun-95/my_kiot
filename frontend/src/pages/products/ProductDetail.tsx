import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import * as productApi from '../../api/product';
import type { ProductResponse } from '../../api/product';
import RoleGate from '../../components/RoleGate';
import { formatVND, formatDate } from '../../utils/format';
import { toFriendlyMessage } from '../../utils/errors';

export default function ProductDetail() {
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = params.id ? Number(params.id) : null;
  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id == null) return;
    setLoading(true);
    (async () => {
      try {
        const p = await productApi.getProduct(id);
        setProduct(p);
      } catch (err) {
        setError(toFriendlyMessage(err));
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const handleDelete = async () => {
    if (id == null) return;
    if (!confirm('Ngừng bán sản phẩm này?')) return;
    try {
      await productApi.deleteProduct(id);
      navigate('/products');
    } catch (err) {
      alert(toFriendlyMessage(err));
    }
  };

  if (loading) return <div className="p-4 text-slate-500">Đang tải...</div>;
  if (error) return <div className="p-4 text-rose-600">{error}</div>;
  if (!product) return <div className="p-4">Không tìm thấy sản phẩm</div>;

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{product.name}</h1>
        <div className="flex gap-2">
          <Link
            to={`/products/${product.id}/edit`}
            className="px-3 py-2 rounded border border-slate-300"
          >
            Sửa
          </Link>
          <RoleGate allow={['OWNER']}>
            <button
              onClick={handleDelete}
              className="px-3 py-2 rounded border border-rose-300 text-rose-700"
            >
              Ngừng bán
            </button>
          </RoleGate>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded p-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <div className="text-slate-500">SKU</div>
          <div className="font-mono">{product.sku}</div>
        </div>
        <div>
          <div className="text-slate-500">Mã vạch</div>
          <div className="font-mono">{product.barcode ?? '-'}</div>
        </div>
        <div>
          <div className="text-slate-500">Nhóm</div>
          <div>{product.category_name ?? '-'}</div>
        </div>
        <div>
          <div className="text-slate-500">Đơn vị</div>
          <div>{product.unit}</div>
        </div>
        <div>
          <div className="text-slate-500">Giá vốn</div>
          <div>{product.cost_price == null ? '—' : formatVND(product.cost_price as number)}</div>
        </div>
        <div>
          <div className="text-slate-500">Giá bán</div>
          <div>{formatVND(product.sale_price as number)}</div>
        </div>
        <div>
          <div className="text-slate-500">Tồn tối thiểu</div>
          <div>{product.min_stock}</div>
        </div>
        <div>
          <div className="text-slate-500">Trạng thái</div>
          <div>
            {product.status === 'ACTIVE'
              ? 'Đang bán'
              : product.status === 'INACTIVE'
                ? 'Ngừng bán'
                : 'Nháp'}
          </div>
        </div>
        <div>
          <div className="text-slate-500">Cho phép bán âm</div>
          <div>{product.allow_negative ? 'Có' : 'Không'}</div>
        </div>
        <div>
          <div className="text-slate-500">Tạo lúc</div>
          <div>{formatDate(product.created_at)}</div>
        </div>
        <div className="col-span-2">
          <div className="text-slate-500">Mô tả</div>
          <div className="whitespace-pre-wrap">{product.description ?? '-'}</div>
        </div>
        {product.image_url && (
          <div className="col-span-2">
            <div className="text-slate-500 mb-1">Ảnh</div>
            <img
              src={product.image_url}
              alt={product.name}
              className="max-h-48 rounded border border-slate-200"
            />
          </div>
        )}
      </div>
    </div>
  );
}
