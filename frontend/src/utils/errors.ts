import type { AxiosError } from 'axios';

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}

const FRIENDLY: Record<string, string> = {
  INSUFFICIENT_STOCK: 'Số lượng tồn không đủ',
  INVALID_CREDENTIALS: 'Sai số điện thoại hoặc mật khẩu',
  ACCOUNT_LOCKED: 'Tài khoản đã bị khóa tạm thời, vui lòng thử lại sau',
  DUPLICATE_SKU: 'Mã SKU đã tồn tại',
  DUPLICATE_BARCODE: 'Mã vạch đã tồn tại',
  DUPLICATE_PHONE: 'Số điện thoại đã tồn tại',
  INSUFFICIENT_PAYMENT: 'Số tiền thanh toán không đủ',
  INVALID_REFRESH_TOKEN: 'Phiên đăng nhập hết hạn',
  REFRESH_TOKEN_REUSE_DETECTED: 'Phiên đăng nhập hết hạn',
  FORBIDDEN: 'Bạn không có quyền thực hiện thao tác này',
  NOT_FOUND: 'Không tìm thấy dữ liệu',
  VALIDATION_ERROR: 'Dữ liệu nhập không hợp lệ',
};

export function extractApiError(err: unknown): ApiErrorBody | null {
  if (!err) return null;
  const ax = err as AxiosError<{ error?: ApiErrorBody }>;
  const body = ax?.response?.data;
  if (body && typeof body === 'object' && 'error' in body && body.error) {
    const e = body.error as ApiErrorBody;
    if (e && typeof e.code === 'string') return e;
  }
  return null;
}

export function friendlyMessage(code: string, fallback?: string): string {
  return FRIENDLY[code] || fallback || 'Có lỗi xảy ra, vui lòng thử lại';
}

export function toFriendlyMessage(err: unknown, fallback?: string): string {
  const parsed = extractApiError(err);
  if (parsed) return friendlyMessage(parsed.code, parsed.message || fallback);
  if (err instanceof Error && err.message) return fallback || err.message;
  return fallback || 'Có lỗi xảy ra, vui lòng thử lại';
}
