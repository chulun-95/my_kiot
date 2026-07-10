"""Danh sách 21 nhóm hàng tạp hóa mặc định (2 cấp), dùng khi:
- Shop mới đăng ký (backend/modules/auth/service.py:register()).
- Backfill shop cũ chưa có nhóm hàng nào (xem alembic/versions/010_backfill_default_categories.py
  — file đó TỰ CHỨA bản copy riêng của danh sách này, KHÔNG import từ đây, vì migration phải
  ổn định theo thời gian, độc lập với thay đổi của code app).

Mỗi tuple: (key, name, depth, parent_key). parent_key=None nghĩa là depth=1 (gốc).
Thứ tự liệt kê quan trọng: mọi depth=1 phải đứng TRƯỚC depth=2 tham chiếu nó, vì vòng lặp
insert tuần tự dựa vào đó để luôn có parent_id sẵn sàng.
"""

DEFAULT_CATEGORIES: list[tuple[str, str, int, str | None]] = [
    ("do_uong", "Đồ uống", 1, None),
    ("nc_ngot", "Nước ngọt & Tăng lực", 2, "do_uong"),
    ("bia_ruou", "Bia & Rượu", 2, "do_uong"),
    ("nc_chai", "Nước đóng chai & Trà", 2, "do_uong"),
    ("tp_kho", "Thực phẩm khô", 1, None),
    ("mi_bun", "Mì tôm & Bún khô", 2, "tp_kho"),
    ("gao_bot", "Gạo & Bột", 2, "tp_kho"),
    ("gia_vi", "Gia vị & Dầu ăn", 1, None),
    ("bk_snack", "Bánh kẹo & Snack", 1, None),
    ("snack_bq", "Snack & Bánh quy", 2, "bk_snack"),
    ("keo_choco", "Kẹo & Chocolate", 2, "bk_snack"),
    ("sua", "Sữa & Sản phẩm sữa", 1, None),
    ("sua_tuoi", "Sữa tươi & Đóng hộp", 2, "sua"),
    ("sua_chua", "Sữa chua & Phô mai", 2, "sua"),
    ("cs_cn", "Chăm sóc cá nhân", 1, None),
    ("ve_sinh", "Vệ sinh cá nhân", 2, "cs_cn"),
    ("dau_goi", "Dầu gội & Dưỡng da", 2, "cs_cn"),
    ("dd_gd", "Đồ dùng gia đình", 1, None),
    ("tay_rua", "Tẩy rửa", 2, "dd_gd"),
    ("dung_cu", "Dụng cụ & Tiện ích", 2, "dd_gd"),
    ("thuoc_la", "Thuốc lá & Diêm quẹt", 1, None),
]
