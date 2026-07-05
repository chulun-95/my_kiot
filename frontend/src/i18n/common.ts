// Chuỗi dùng chung nhiều trang (VN). Mỗi module có file riêng src/i18n/<module>.ts.
// KHÔNG hard-code text trong component — import từ đây hoặc từ file module tương ứng.
export const common = {
  save: 'Lưu',
  cancel: 'Huỷ',
  delete: 'Xoá',
  close: 'Đóng',
  back: 'Quay lại',
  confirm: 'Xác nhận',
  add: 'Thêm',
  edit: 'Sửa',
  done: 'Hoàn tất',
  processing: 'Đang xử lý...',
  loading: 'Đang tải...',
  retry: 'Thử lại',
  search: 'Tìm kiếm',
  guestCustomer: 'Khách lẻ',
  logout: 'Đăng xuất',
  required: 'Bắt buộc',
  noData: 'Không có dữ liệu',
  saving: 'Đang lưu...',
} as const;
