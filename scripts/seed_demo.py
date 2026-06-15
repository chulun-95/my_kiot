#!/usr/bin/env python3
"""
Seed dữ liệu demo — Tạp Hóa Mỹ Linh
Giả lập 5 tháng hoạt động thật: 02/01/2026 – 12/06/2026

Tạo:
  • 1 tenant + 3 users (1 owner, 2 cashier)
  • 21 danh mục (8 cha + 13 con)
  • 20 nhà cung cấp (5 có công nợ còn lại)
  • 100 sản phẩm
  • 30 khách hàng thân thiết (8 có công nợ)
  • ~60 phiếu nhập kho
  • ~3 500 hóa đơn bán hàng
  • Kardex (stock_movements) nhất quán với tồn kho

Chạy: python scripts/seed_demo.py [--reset]
"""
from __future__ import annotations

import asyncio
import math
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import asyncpg
import bcrypt

# Fix Windows console encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

# ─── CONFIG ──────────────────────────────────────────────────────────────────
random.seed(42)
TZ = timezone.utc
START = date(2026, 1, 2)
END   = date(2026, 6, 12)
TENANT_SLUG = "tap-hoa-my-linh"

def _hash(pw: str) -> str:
    # rounds=4 để seed nhanh (dev only, production dùng 12)
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=4)).decode()

def _dt(d: date, hour=9, minute=0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=TZ)

def D(v) -> Decimal:
    return Decimal(str(v))

def roundd(v: Decimal) -> Decimal:
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

# ─── DB URL ───────────────────────────────────────────────────────────────────
def _db_url() -> str:
    for p in [Path(__file__).parent.parent / ".env", Path(".env")]:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip().strip("'\"")
                    return url.replace("postgresql+asyncpg://", "postgresql://")
    return "postgresql://pos_user:pos_secret@localhost:5432/pos_db"

# ─── STATIC DATA ─────────────────────────────────────────────────────────────

CATEGORIES = [
    # (key, name, depth, parent_key)
    ("do_uong",      "Đồ uống",                 1, None),
    ("nc_ngot",      "Nước ngọt & Tăng lực",    2, "do_uong"),
    ("bia_ruou",     "Bia & Rượu",              2, "do_uong"),
    ("nc_chai",      "Nước đóng chai & Trà",    2, "do_uong"),
    ("tp_kho",       "Thực phẩm khô",           1, None),
    ("mi_bun",       "Mì tôm & Bún khô",        2, "tp_kho"),
    ("gao_bot",      "Gạo & Bột",               2, "tp_kho"),
    ("gia_vi",       "Gia vị & Dầu ăn",         1, None),
    ("bk_snack",     "Bánh kẹo & Snack",        1, None),
    ("snack_bq",     "Snack & Bánh quy",        2, "bk_snack"),
    ("keo_choco",    "Kẹo & Chocolate",         2, "bk_snack"),
    ("sua",          "Sữa & Sản phẩm sữa",      1, None),
    ("sua_tuoi",     "Sữa tươi & Đóng hộp",    2, "sua"),
    ("sua_chua",     "Sữa chua & Phô mai",      2, "sua"),
    ("cs_cn",        "Chăm sóc cá nhân",        1, None),
    ("ve_sinh",      "Vệ sinh cá nhân",         2, "cs_cn"),
    ("dau_goi",      "Dầu gội & Dưỡng da",     2, "cs_cn"),
    ("dd_gd",        "Đồ dùng gia đình",        1, None),
    ("tay_rua",      "Tẩy rửa",                 2, "dd_gd"),
    ("dung_cu",      "Dụng cụ & Tiện ích",      2, "dd_gd"),
    ("thuoc_la",     "Thuốc lá & Diêm quẹt",   1, None),
]

SUPPLIERS = [
    # (key, name, phone, address, tax_code, has_debt)
    ("cocacola",  "Cty TNHH Coca-Cola Beverages VN",       "02838940321", "156 Nguyễn Lương Bằng, Q7, HCM",  "0300788497", True),
    ("pepsi",     "Cty TNHH Nước Giải Khát PepsiCo VN",   "02839971800", "Đường D1, KCN Việt Nam-Singapore", "0302654006", False),
    ("masan",     "Tập đoàn Masan Consumer",               "02835172989", "12 Nguyễn Đình Chiểu, Q1, HCM",   "0300827791", True),
    ("vinamilk",  "Cty CP Sữa Việt Nam (Vinamilk)",        "02854553888", "10 Tân Trào, Q7, HCM",            "0300588569", False),
    ("unilever",  "Cty TNHH Unilever VN",                  "02839112744", "156 Nguyễn Lương Bằng, Q7, HCM",  "0300584301", True),
    ("sabeco",    "Tổng Cty Bia-Rượu-NGK Sài Gòn",        "02839325956", "187 Nguyễn Chí Thanh, Q5, HCM",   "0300459891", False),
    ("habeco",    "Cty CP Bia Hà Nội (Habeco)",            "02438254596", "183 Hoàng Hoa Thám, Ba Đình, HN",  "0100109106", False),
    ("acecook",   "Cty CP Acecook Việt Nam",               "02838960356", "KCN Tây Bắc Củ Chi, HCM",         "0300422356", False),
    ("nestle",    "Cty TNHH Nestle Việt Nam",              "02839232888", "151 Võ Thị Sáu, Q3, HCM",         "0301400082", False),
    ("bibica",    "Cty CP Bibica",                         "02839603636", "38 Tân Thắng, Q Tân Phú, HCM",    "0300473831", False),
    ("pg",        "Cty TNHH P&G Việt Nam",                 "02838116888", "Tầng 8, Saigon Trade Center, Q1",  "0300558140", False),
    ("giay_sg",   "Cty CP Giấy Sài Gòn",                  "02838714111", "52/5 Tân Thới Nhất, Q12, HCM",    "0300817614", False),
    ("th_milk",   "Cty CP TH True Milk",                   "02435645234", "KCN Nghĩa Đàn, Nghệ An",          "2900506501", False),
    ("luong_thuc","Cty CP Lương Thực Sài Gòn",             "02839234444", "235 Nguyễn Văn Cừ, Q5, HCM",      "0300436671", True),
    ("urc",       "Cty TNHH URC Việt Nam",                 "02839334455", "KCN Bình Dương",                   "0313186898", False),
    ("minh_phuc", "Đại lý Minh Phúc",                      "0903456781",  "45 Nguyễn Văn Lương, Q6, HCM",    None,         False),
    ("hoang_long","Đại lý Hoàng Long",                     "0914567892",  "78 Bình Phú, Q6, HCM",            None,         True),
    ("phu_quy",   "Đại lý Phú Quý",                       "0925678903",  "112 Hậu Giang, Q6, HCM",          None,         False),
    ("binh_tay",  "Cty CP Thực phẩm Bình Tây",            "02839600123", "280 Lý Thường Kiệt, Q11, HCM",    "0300427019", False),
    ("tan_hiep",  "Cty CP Tân Hiệp Phát",                  "02743800380", "219 Bình Dương, TDM, BD",         "3700100588", False),
]

# (name, cat_key, unit, cost, sale, barcode, min_stock, sup_key, monthly_sales)
PRODUCTS_DATA = [
    # ── Nước ngọt & Tăng lực ──────────────────────────────────────────────
    ("Coca-Cola lon 330ml",            "nc_ngot",   "lon",  8500,  12000, "8934673160012", 24, "cocacola",  300),
    ("Pepsi lon 330ml",                "nc_ngot",   "lon",  7500,  11000, "8934504030012", 24, "pepsi",     250),
    ("7UP lon 330ml",                  "nc_ngot",   "lon",  7500,  11000, "8934504030019", 12, "pepsi",     150),
    ("Fanta Cam lon 330ml",            "nc_ngot",   "lon",  7500,  11000, "8934673160029", 12, "cocacola",  120),
    ("Mirinda Cam lon 330ml",          "nc_ngot",   "lon",  7000,  10000, "8934504030026", 12, "pepsi",     100),
    ("Sprite lon 330ml",               "nc_ngot",   "lon",  7500,  11000, "8934673160036", 12, "cocacola",  100),
    ("Sting Dâu lon 330ml",            "nc_ngot",   "lon",  8500,  13000, "8934527110012", 12, "pepsi",     120),
    ("Sting Gold lon 330ml",           "nc_ngot",   "lon",  8500,  13000, "8934527110036", 12, "pepsi",     100),
    ("Red Bull lon 250ml",             "nc_ngot",   "lon", 10000,  15000, "5010477354004", 12, "hoang_long", 80),
    ("Number 1 lon 330ml",             "nc_ngot",   "lon",  7500,  11000, "8934588110012", 12, "tan_hiep",  180),
    ("Trà xanh Không Độ 500ml",        "nc_ngot",   "chai", 7000,  10000, "8934588140012", 12, "tan_hiep",  200),
    ("Nước tăng lực Warrior 330ml",    "nc_ngot",   "lon",  7000,  10000, "8935049110036", 10, "phu_quy",   80),
    # ── Nước đóng chai & Trà ─────────────────────────────────────────────
    ("C2 Trà xanh 360ml",              "nc_chai",   "chai", 5500,   8000, "8935217280012", 12, "urc",       220),
    ("Trà Lipton Ice Tea 1L",          "nc_chai",   "chai",14000,  20000, "8934527140012",  6, "pepsi",      60),
    ("Nước suối Lavie 500ml",          "nc_chai",   "chai", 3000,   5000, "8934561100012", 48, "minh_phuc", 500),
    ("Nước suối Aquafina 500ml",       "nc_chai",   "chai", 3000,   5000, "8934504060012", 48, "pepsi",     400),
    ("Nước khoáng Vĩnh Hảo 1.5L",     "nc_chai",   "chai", 6000,   9000, "8934561100029", 12, "minh_phuc", 150),
    ("Dasani 1L",                      "nc_chai",   "chai", 5500,   8000, "8934673200012", 12, "cocacola",  100),
    ("Nước Yến sào Sanest 180ml",      "nc_chai",   "hộp", 15000,  22000, "8935049200012",  6, "phu_quy",   40),
    # ── Bia & Rượu ───────────────────────────────────────────────────────
    ("Bia Tiger lon 330ml",            "bia_ruou",  "lon", 14000,  20000, "9556028020012", 24, "sabeco",   180),
    ("Bia Heineken lon 330ml",         "bia_ruou",  "lon", 17000,  25000, "5000234001028", 12, "habeco",   120),
    ("Bia 333 lon 330ml",              "bia_ruou",  "lon", 11000,  16000, "8934588030012", 24, "sabeco",   200),
    ("Bia Sài Gòn Đỏ lon 330ml",      "bia_ruou",  "lon", 11000,  16000, "8934588030029", 24, "sabeco",   200),
    ("Bia Hà Nội lon 330ml",           "bia_ruou",  "lon", 10000,  15000, "8934588050012", 24, "habeco",   150),
    ("Bia Sài Gòn Lager chai 450ml",   "bia_ruou",  "chai",12000,  18000, "8934588030036", 12, "sabeco",    80),
    # ── Mì tôm & Bún khô ─────────────────────────────────────────────────
    ("Mì Hảo Hảo Tôm chua cay 75g",   "mi_bun",    "gói", 3500,   5500, "8934563120012", 60, "acecook",  400),
    ("Mì Hảo Hảo Sườn heo 77g",       "mi_bun",    "gói", 3500,   5500, "8934563120029", 60, "acecook",  300),
    ("Mì 3 Miền 65g",                  "mi_bun",    "gói", 2800,   4500, "8934588080012", 60, "masan",    350),
    ("Mì Omachi Tôm 80g",              "mi_bun",    "gói", 5500,   8000, "8934563130012", 30, "acecook",  200),
    ("Mì Omachi Sốt Bolognese 91g",    "mi_bun",    "gói", 5500,   8000, "8934563130029", 30, "acecook",  150),
    ("Mì Kokomi 65g",                  "mi_bun",    "gói", 2800,   4500, "8935228200012", 60, "masan",    250),
    ("Phở Anh Quân 66g",               "mi_bun",    "gói", 4500,   7000, "8934563150012", 20, "acecook",  100),
    ("Bún gạo Bích Chi khô 200g",      "mi_bun",    "gói", 8000,  12000, "8936023820012", 10, "phu_quy",   50),
    # ── Gạo & Bột ────────────────────────────────────────────────────────
    ("Gạo Nàng Hoa 5kg",               "gao_bot",   "túi",62000,  85000, None,             5, "luong_thuc", 30),
    ("Gạo Jasmine Thái 5kg",           "gao_bot",   "túi",75000, 100000, None,             5, "luong_thuc", 20),
    ("Gạo ST25 cao cấp 5kg",           "gao_bot",   "túi",95000, 130000, None,             5, "luong_thuc", 10),
    ("Bột mì Bình Đông 1kg",           "gao_bot",   "túi",15000,  22000, "8934620200012", 10, "phu_quy",   30),
    ("Đường tinh luyện 1kg",           "gao_bot",   "túi",20000,  28000, "8934620300012", 10, "masan",     40),
    ("Muối tinh biển 1kg",             "gao_bot",   "túi", 8000,  12000, "8936023100012", 10, "phu_quy",   25),
    # ── Gia vị & Dầu ăn ──────────────────────────────────────────────────
    ("Nước mắm Phú Quốc 40° 500ml",    "gia_vi",    "chai",35000,  50000, "8935049110012", 10, "phu_quy",   40),
    ("Nước mắm Nam Ngư 500ml",         "gia_vi",    "chai",22000,  32000, "8934673400012", 10, "masan",     60),
    ("Nước mắm Chinsu 500ml",          "gia_vi",    "chai",22000,  32000, "8934673400029", 10, "masan",     50),
    ("Tương ớt Chinsu 250g",           "gia_vi",    "chai",12000,  18000, "8934673410012", 10, "masan",     70),
    ("Tương cà Heinz 300g",            "gia_vi",    "chai",18000,  28000, "8809576900012",  6, "hoang_long", 30),
    ("Dầu hào Lee Kum Kee 255ml",      "gia_vi",    "chai",28000,  42000, "6900050120012",  6, "hoang_long", 25),
    ("Nước tương Maggi 500ml",         "gia_vi",    "chai",18000,  27000, "8934673420012",  6, "nestle",    40),
    ("Hạt nêm Knorr gà 400g",          "gia_vi",    "hộp",38000,  55000, "8934673430012",  6, "unilever",  35),
    ("Bột ngọt Ajinomoto 450g",        "gia_vi",    "túi",28000,  40000, "8934000100012",  6, "hoang_long", 30),
    ("Dầu ăn Meizan 1L",               "gia_vi",    "chai",32000,  45000, "8934673440012",  6, "masan",     50),
    ("Dầu ăn Neptune 1L",              "gia_vi",    "chai",34000,  48000, "8934673440029",  6, "masan",     40),
    # ── Snack & Bánh quy ─────────────────────────────────────────────────
    ("Snack Oishi tôm 40g",            "snack_bq",  "gói", 5500,   8000, "8934588500012", 20, "phu_quy",  120),
    ("Snack Poca khoai tây 42g",       "snack_bq",  "gói", 6500,  10000, "8934504500012", 20, "pepsi",    100),
    ("Bánh gạo Tý Phú 200g",           "snack_bq",  "gói",12000,  18000, "8934620500012", 10, "phu_quy",   50),
    ("Bánh quy Marie 200g",            "snack_bq",  "gói",12000,  18000, "8934620510012", 10, "bibica",    60),
    ("Bánh Oreo socola 133g",          "snack_bq",  "gói",14000,  22000, "7622400368427", 10, "hoang_long", 80),
    ("Bánh Cream-O kem 30g",           "snack_bq",  "gói", 5500,   8000, "8935049500012", 20, "phu_quy",  100),
    ("Bánh quy Tiger 300g",            "snack_bq",  "hộp",35000,  52000, "8934588510012",  6, "binh_tay",  30),
    ("Bánh bông lan Gato Mini 360g",   "snack_bq",  "hộp",42000,  62000, "8934620520012",  6, "bibica",    25),
    ("Bánh Kinh Đô nhân dứa 150g",    "snack_bq",  "hộp",25000,  38000, "8934588520012",  6, "masan",     40),
    # ── Kẹo & Chocolate ──────────────────────────────────────────────────
    ("Kẹo dừa Bến Tre 200g",           "keo_choco", "gói",22000,  32000, "8935049600012", 10, "phu_quy",   40),
    ("Kẹo Alpenliebe Dâu 118g",        "keo_choco", "túi",16000,  25000, "8936023600012", 10, "hoang_long", 60),
    ("Kẹo cao su Doublemint 45g",      "keo_choco", "hộp", 8000,  12000, "4800459120012", 10, "hoang_long", 70),
    ("Socola KitKat 4 thanh 41.5g",    "keo_choco", "gói",15000,  22000, "8934673600012", 10, "nestle",    60),
    ("Socola M&M's 45g",               "keo_choco", "gói",18000,  27000, "0040000472513",  6, "hoang_long", 40),
    ("Kẹo dẻo Haribo 80g",             "keo_choco", "gói",20000,  30000, "4001686330999",  6, "hoang_long", 30),
    # ── Sữa tươi & Đóng hộp ─────────────────────────────────────────────
    ("Sữa tươi Vinamilk ít đường 1L",  "sua_tuoi",  "hộp",25000,  36000, "8934673700012", 12, "vinamilk",  80),
    ("Sữa tươi TH True Milk 1L",       "sua_tuoi",  "hộp",27000,  39000, "8936144100012", 12, "th_milk",   70),
    ("Sữa đặc Ông Thọ đỏ 380g",        "sua_tuoi",  "lon",18000,  26000, "8934673710012", 12, "vinamilk",  60),
    ("Sữa đặc Ngôi Sao Phương Nam",    "sua_tuoi",  "lon",16000,  24000, "8934673710029", 12, "vinamilk",  50),
    ("Milo bột 400g",                  "sua_tuoi",  "hộp",55000,  80000, "8934673730012",  6, "nestle",    30),
    ("Nestle Milo hộp 240ml",          "sua_tuoi",  "hộp", 8000,  12000, "8934673730029", 24, "nestle",   100),
    ("Sữa bột Dielac 900g",            "sua_tuoi",  "hộp",185000, 260000, "8934673740012",  3, "vinamilk",  10),
    # ── Sữa chua & Phô mai ───────────────────────────────────────────────
    ("Sữa chua Vinamilk có đường 100g","sua_chua",  "hộp", 5000,   8000, "8934673720012", 20, "vinamilk", 150),
    ("Sữa chua uống Vinamilk 180ml",   "sua_chua",  "hộp", 6500,  10000, "8934673720029", 20, "vinamilk", 100),
    ("Yakult 65ml (5 hộp)",            "sua_chua",  "lốc",18000,  27000, "8936144110012", 10, "hoang_long", 50),
    ("Phô mai con bò cười 133g",       "sua_chua",  "hộp",32000,  48000, "3178530402222",  6, "hoang_long", 25),
    # ── Vệ sinh cá nhân ──────────────────────────────────────────────────
    ("Kem đánh răng Colgate 250g",     "ve_sinh",   "tuýp",28000,  40000, "8934673810012", 10, "unilever", 50),
    ("Kem đánh răng P/S 250g",         "ve_sinh",   "tuýp",22000,  32000, "8934673810029", 10, "unilever", 40),
    ("Xà phòng Lifebuoy 90g",          "ve_sinh",   "cái",  8000,  12000, "8934673820012", 12, "unilever", 80),
    ("Sữa tắm Lifebuoy 500ml",         "ve_sinh",   "chai",42000,  62000, "8934673820029",  6, "unilever", 40),
    ("Nước rửa tay Lifebuoy 500ml",    "ve_sinh",   "chai",45000,  65000, "8934673820036",  6, "unilever", 35),
    ("Lăn khử mùi Dove 40ml",          "ve_sinh",   "cây", 38000,  55000, "8934673830012",  6, "unilever", 25),
    ("Bàn chải đánh răng Oral-B",      "ve_sinh",   "cái", 25000,  38000, "8006540122334",  6, "pg",       30),
    # ── Dầu gội & Dưỡng da ───────────────────────────────────────────────
    ("Dầu gội Sunsilk 650ml",          "dau_goi",   "chai",68000,  98000, "8934673800012",  6, "unilever", 25),
    ("Dầu gội Clear Men 630ml",        "dau_goi",   "chai",72000, 105000, "8934673800029",  6, "unilever", 20),
    ("Dầu gội Pantene 650ml",          "dau_goi",   "chai",70000, 102000, "8006540122327",  6, "pg",       18),
    ("Kem dưỡng ẩm Pond's 50g",        "dau_goi",   "hộp", 55000,  80000, "8934673800036",  6, "unilever", 15),
    # ── Tẩy rửa ─────────────────────────────────────────────────────────
    ("Nước rửa chén Sunlight 1L",      "tay_rua",   "chai",28000,  40000, "8934673900012",  6, "unilever", 60),
    ("Bột giặt Omo Matic 3kg",         "tay_rua",   "túi",120000, 170000, "8934673900029",  3, "unilever", 15),
    ("Nước giặt Surf Lavender 2.4L",   "tay_rua",   "chai",75000, 108000, "8934673900036",  3, "unilever", 12),
    ("Nước xả Comfort 1L",             "tay_rua",   "chai",35000,  52000, "8934673900043",  3, "unilever", 35),
    ("Nước lau sàn Vim 1L",            "tay_rua",   "chai",32000,  48000, "8934673910012",  3, "unilever", 20),
    # ── Dụng cụ & Tiện ích ───────────────────────────────────────────────
    ("Túi rác đen 65x90 50 cái",       "dung_cu",   "cuộn",15000,  22000, "8934620900012", 10, "giay_sg",  40),
    ("Giấy vệ sinh Pulppy 10 cuộn",    "dung_cu",   "gói", 42000,  60000, "8934620910012",  6, "giay_sg",  30),
    ("Khăn giấy Pulppy hộp 100 tờ",   "dung_cu",   "hộp", 18000,  27000, "8934620920012",  6, "giay_sg",  35),
    ("Pin Duracell AA 4 viên",         "dung_cu",   "vỉ",  35000,  52000, "0041333004842",  6, "hoang_long", 20),
    ("Bao bì túi PE 100 cái",          "dung_cu",   "bó",  12000,  18000, None,            10, "minh_phuc", 25),
    # ── Thuốc lá ────────────────────────────────────────────────────────
    ("Thuốc lá Vinataba đỏ",           "thuoc_la",  "bao", 25000,  35000, "8934588900012", 10, "phu_quy",  80),
    ("Thuốc lá Hero xanh",             "thuoc_la",  "bao", 23000,  33000, "8934588900029", 10, "phu_quy",  60),
    ("Thuốc lá Marlboro đỏ",           "thuoc_la",  "bao", 28000,  40000, "0012581400000",  6, "phu_quy",  40),
    ("Thuốc lá Thăng Long 10",         "thuoc_la",  "bao", 20000,  30000, "8934588900036", 10, "phu_quy",  50),
    ("Diêm Thống Nhất hộp",            "thuoc_la",  "hộp",  1500,   3000, "8934620950012", 20, "minh_phuc", 60),
    ("Bật lửa Mini Gas",               "thuoc_la",  "cái",  5000,   8000, None,            10, "minh_phuc", 45),
]

CUSTOMERS = [
    # (name, phone, address)
    ("Nguyễn Thị Lan",    "0901111111", "45 Bình Phú, Q6"),
    ("Trần Văn Bình",     "0912222222", "78 Hậu Giang, Q6"),
    ("Lê Thị Ngọc",       "0923333333", "12 Nguyễn Văn Lương, Q6"),
    ("Phạm Minh Tuấn",    "0934444444", "34 Lê Văn Sỹ, Q3"),
    ("Vũ Thị Hương",      "0945555555", "56 Cách Mạng Tháng 8, Q10"),
    ("Đặng Văn Hùng",     "0956666666", "89 Đinh Tiên Hoàng, Q1"),
    ("Bùi Thị Thu",       "0967777777", "23 Nguyễn Trãi, Q5"),
    ("Hoàng Minh Quân",   "0978888888", "67 Lý Thường Kiệt, Q11"),
    ("Ngô Thị Hạnh",      "0989999999", "14 Trần Phú, Q5"),
    ("Đinh Văn Phong",    "0901234560", "90 Ngô Quyền, Q5"),
    ("Chu Thị Liên",      "0912345670", "32 Nguyễn Đình Chiểu, Q3"),
    ("Mai Văn Dũng",      "0923456780", "11 Trương Định, Q3"),
    ("Cao Thị Vân",       "0934567890", "55 Võ Thị Sáu, Q3"),
    ("Lý Minh Khoa",      "0945678900", "77 Điện Biên Phủ, Q3"),
    ("Tống Thị Hà",       "0956789010", "33 Nguyễn Kiệm, Gò Vấp"),
    ("Dương Văn Long",    "0967890120", "19 Quang Trung, Gò Vấp"),
    ("Phan Thị Bích",     "0978901230", "88 Phạm Văn Đồng, Gò Vấp"),
    ("Trịnh Minh Hiếu",   "0989012340", "44 Nguyễn Oanh, Gò Vấp"),
    ("Võ Thị Kim",        "0901122334", "66 Lê Đức Thọ, Gò Vấp"),
    ("Lưu Văn Sơn",       "0912233445", "28 Thống Nhất, Gò Vấp"),
    ("Đỗ Thị Thanh",      "0923344556", "51 Nguyễn Hữu Cảnh, Bình Thạnh"),
    ("Hồ Văn Tú",         "0934455667", "73 Xô Viết Nghệ Tĩnh, Bình Thạnh"),
    ("Lê Thị Mỹ",         "0945566778", "15 Bình Lợi, Bình Thạnh"),
    ("Nguyễn Văn Toàn",   "0956677889", "39 Nơ Trang Long, Bình Thạnh"),
    ("Phạm Thị Dung",     "0967788990", "62 Phan Văn Trị, Bình Thạnh"),
    ("Trần Minh Khải",    "0978899001", "84 Lê Quang Định, Bình Thạnh"),
    ("Chu Văn Thành",     "0989900112", "47 Đinh Bộ Lĩnh, Bình Thạnh"),
    ("Nguyễn Thị Phương", "0901011223", "20 Nguyễn Xí, Bình Thạnh"),
    ("Lê Văn Tài",        "0912122334", "96 Bạch Đằng, Bình Thạnh"),
    ("Trần Thị Xuân",     "0923233445", "58 Tô Hiến Thành, Q10"),
]

# Khách hàng có công nợ (index vào CUSTOMERS)
DEBT_CUSTOMER_INDEXES = {1, 3, 7, 11, 15, 19, 23, 27}

# ─── HELPER ───────────────────────────────────────────────────────────────────

def _rand_time(d: date) -> datetime:
    h = random.randint(7, 21)
    m = random.randint(0, 59)
    s = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, h, m, s, tzinfo=TZ)

def _invoices_per_day(d: date) -> int:
    tet_pre  = date(2026, 1, 20) <= d <= date(2026, 1, 28)
    tet_hol  = date(2026, 1, 29) <= d <= date(2026, 2,  4)
    post_tet = date(2026, 2,  5) <= d <= date(2026, 2, 14)
    weekend  = d.weekday() >= 5  # Sat / Sun
    if tet_hol:   return random.randint(3, 10)
    if tet_pre:   return random.randint(60, 90)
    if post_tet:  return random.randint(12, 22)
    if weekend:   return random.randint(40, 60)
    return random.randint(22, 38)

# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main() -> None:
    reset = "--reset" in sys.argv
    db_url = _db_url()

    print(f"Kết nối DB: {db_url[:40]}...")
    conn = await asyncpg.connect(db_url)

    try:
        # ── Kiểm tra tenant đã tồn tại ───────────────────────────────────
        existing = await conn.fetchval(
            "SELECT id FROM tenants WHERE slug = $1", TENANT_SLUG
        )
        if existing and not reset:
            print(f"✗ Tenant '{TENANT_SLUG}' đã tồn tại. Dùng --reset để xóa và tạo lại.")
            return
        if existing and reset:
            print("Đang xóa dữ liệu cũ...")
            await _reset_tenant(conn, existing)

        await _seed(conn)
    finally:
        await conn.close()


async def _reset_tenant(conn, tenant_id: int) -> None:
    # Xóa theo thứ tự để tránh FK violation
    tables = [
        "stock_movements", "inventory", "goods_receipt_items",
        "goods_receipts", "invoice_items", "payments",
        "return_order_items", "return_orders", "invoices",
        "customers", "suppliers", "product_units", "product_images",
        "products", "categories", "cash_transactions",
        "price_history", "code_sequences",
        "refresh_tokens",
    ]
    for t in tables:
        if t in ("code_sequences",):
            await conn.execute(f"DELETE FROM {t} WHERE tenant_id = $1", tenant_id)
        elif t == "refresh_tokens":
            await conn.execute(
                "DELETE FROM refresh_tokens WHERE user_id IN "
                "(SELECT id FROM users WHERE tenant_id = $1)", tenant_id
            )
        else:
            try:
                await conn.execute(f"DELETE FROM {t} WHERE tenant_id = $1", tenant_id)
            except Exception:
                pass
    await conn.execute("DELETE FROM users WHERE tenant_id = $1", tenant_id)
    await conn.execute("DELETE FROM tenants WHERE id = $1", tenant_id)


async def _seed(conn) -> None:
    # ── 1. Tenant ─────────────────────────────────────────────────────────
    now = datetime.now(TZ)
    tenant_id: int = await conn.fetchval(
        """INSERT INTO tenants
           (name, slug, phone, address, settings, is_active, created_at, updated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""",
        "Tạp Hóa Mỹ Linh", TENANT_SLUG, "0901234567",
        "123 Nguyễn Văn Lương, Phường 10, Quận 6, TP.HCM",
        '{"allow_debt":true,"default_payment_method":"CASH","low_stock_threshold_default":5}',
        True, now, now,
    )
    print(f"✓ Tenant id={tenant_id}")

    # ── 2. Users ──────────────────────────────────────────────────────────
    owner_hash   = _hash("owner123")
    cashier_hash = _hash("cashier123")

    owner_id: int = await conn.fetchval(
        """INSERT INTO users
           (tenant_id, phone, email, full_name, password_hash, role, is_active, created_at, updated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id""",
        tenant_id, "0901234567", "mylinh@taphoamylinh.vn",
        "Nguyễn Thị Mỹ Linh", owner_hash, "OWNER", True, now, now,
    )
    cashier1_id: int = await conn.fetchval(
        """INSERT INTO users
           (tenant_id, phone, email, full_name, password_hash, role, is_active, created_at, updated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id""",
        tenant_id, "0912345678", None,
        "Trần Văn Nam", cashier_hash, "CASHIER", True, now, now,
    )
    cashier2_id: int = await conn.fetchval(
        """INSERT INTO users
           (tenant_id, phone, email, full_name, password_hash, role, is_active, created_at, updated_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id""",
        tenant_id, "0923456789", None,
        "Lê Thị Hoa", cashier_hash, "CASHIER", True, now, now,
    )
    user_ids = [owner_id, cashier1_id, cashier2_id]
    print(f"✓ Users: owner={owner_id}, cashier1={cashier1_id}, cashier2={cashier2_id}")

    # ── 3. Categories ─────────────────────────────────────────────────────
    cat_id: dict[str, int] = {}
    for key, name, depth, parent_key in CATEGORIES:
        parent_id = cat_id.get(parent_key) if parent_key else None
        cid = await conn.fetchval(
            """INSERT INTO categories
               (tenant_id, parent_id, name, depth, sort_order, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id""",
            tenant_id, parent_id, name, depth, 0, now, now,
        )
        cat_id[key] = cid
    print(f"✓ Categories: {len(cat_id)}")

    # ── 4. Suppliers ──────────────────────────────────────────────────────
    sup_id: dict[str, int] = {}
    for key, name, phone, addr, tax, _ in SUPPLIERS:
        sid = await conn.fetchval(
            """INSERT INTO suppliers
               (tenant_id, name, phone, address, tax_code, total_debt, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""",
            tenant_id, name, phone, addr, tax, D(0), now, now,
        )
        sup_id[key] = sid
    print(f"✓ Suppliers: {len(sup_id)}")

    # ── 5. Products ───────────────────────────────────────────────────────
    prod_ids: list[int] = []
    prod_meta: list[dict] = []  # full metadata for generation
    for i, (name, cat_key, unit, cost, sale, barcode, min_stock, sup_key, monthly_sales) in enumerate(PRODUCTS_DATA):
        sku = f"SP{i+1:04d}"
        pid = await conn.fetchval(
            """INSERT INTO products
               (tenant_id, category_id, sku, barcode, name, unit,
                cost_price, sale_price, min_stock, status, allow_negative,
                created_by, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14) RETURNING id""",
            tenant_id, cat_id.get(cat_key), sku, barcode, name, unit,
            D(cost), D(sale), min_stock, "ACTIVE", False,
            owner_id, now, now,
        )
        prod_ids.append(pid)
        prod_meta.append({
            "id": pid, "name": name, "sku": sku, "unit": unit,
            "cost": D(cost), "sale": D(sale),
            "sup_key": sup_key, "monthly_sales": monthly_sales,
        })
    print(f"✓ Products: {len(prod_ids)}")

    # ── 6. Customers ──────────────────────────────────────────────────────
    cust_ids: list[int] = []
    for i, (name, phone, addr) in enumerate(CUSTOMERS):
        cid = await conn.fetchval(
            """INSERT INTO customers
               (tenant_id, name, phone, address, total_spent, total_orders,
                created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""",
            tenant_id, name, phone, addr, D(0), 0, now, now,
        )
        cust_ids.append(cid)
    print(f"✓ Customers: {len(cust_ids)}")

    # ── 7. Sinh dữ liệu lịch sử ─────────────────────────────────────────
    inv_balance: dict[int, Decimal] = {p["id"]: D(0) for p in prod_meta}
    code_seq: dict[tuple, int] = defaultdict(int)  # (prefix, YYYYMMDD) → last_num

    # receipt_counter để theo dõi code_sequences
    total_receipts = 0
    total_invoices = 0
    total_debt_amount = D(0)
    supplier_debt: dict[str, Decimal] = defaultdict(Decimal)
    cust_stats: dict[int, dict] = {
        cid: {"spent": D(0), "orders": 0, "last_order": None} for cid in cust_ids
    }

    # ── Generate receipts schedule ────────────────────────────────────────
    # Mỗi NCC nhập hàng 2–3 lần/tháng, mỗi lần 8–15 mặt hàng
    print("Đang tạo phiếu nhập kho...")
    receipt_days: list[date] = []
    cur = START
    while cur <= END:
        # Nhập hàng vào thứ 2/thứ 5 mỗi tuần (xấp xỉ)
        if cur.weekday() in (0, 3):  # Mon, Thu
            receipt_days.append(cur)
        cur += timedelta(days=1)

    for rday in receipt_days:
        # Mỗi ngày nhập 1–2 NCC
        n_suppliers = random.randint(1, 2)
        chosen_sups = random.sample(list(sup_id.keys()), n_suppliers)

        for sup_key in chosen_sups:
            # Chọn sản phẩm của NCC này (hoặc ngẫu nhiên nếu ít)
            sup_prods = [p for p in prod_meta if p["sup_key"] == sup_key]
            if not sup_prods:
                sup_prods = random.sample(prod_meta, 5)
            # Chọn 5–12 sản phẩm để nhập
            n_items = min(len(sup_prods), random.randint(5, 12))
            items = random.sample(sup_prods, n_items)

            date_part = rday.strftime("%Y%m%d")
            code_seq[("NK", date_part)] += 1
            code = f"NK{date_part}-{code_seq[('NK', date_part)]:03d}"

            receipt_total = D(0)
            receipt_items = []
            for p in items:
                # Nhập đủ dùng 2–3 tuần
                weekly = math.ceil(p["monthly_sales"] / 4)
                qty = D(random.randint(weekly * 2, weekly * 3 + 20))
                line_total = roundd(qty * p["cost"])
                receipt_total += line_total
                receipt_items.append((p["id"], qty, p["cost"], line_total))

            # Công nợ NCC: NCC có has_debt=True → 30% phiếu chưa trả hết
            sup_has_debt = next(s[5] for s in SUPPLIERS if s[0] == sup_key)
            if sup_has_debt and random.random() < 0.30:
                paid = roundd(receipt_total * D(str(random.choice([0.5, 0.7, 0]))))
            else:
                paid = receipt_total

            rcpt_time = _rand_time(rday)
            receipt_id: int = await conn.fetchval(
                """INSERT INTO goods_receipts
                   (tenant_id, code, supplier_id, total, paid_amount, payment_method,
                    status, completed_at, created_by, created_at, updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING id""",
                tenant_id, code, sup_id[sup_key], receipt_total, paid,
                "CASH", "COMPLETED", rcpt_time, owner_id, rcpt_time, rcpt_time,
            )

            debt_this = receipt_total - paid
            if debt_this > 0:
                supplier_debt[sup_key] += debt_this

            for pid, qty, cost, line_total in receipt_items:
                await conn.execute(
                    """INSERT INTO goods_receipt_items
                       (receipt_id, product_id, quantity, cost_price, line_total)
                       VALUES ($1,$2,$3,$4,$5)""",
                    receipt_id, pid, qty, cost, line_total,
                )
                # StockMovement
                inv_balance[pid] += qty
                await conn.execute(
                    """INSERT INTO stock_movements
                       (tenant_id, product_id, quantity, unit_cost, type, ref_type,
                        ref_id, balance_after, created_at, created_by)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    tenant_id, pid, qty, cost, "RECEIPT", "GOODS_RECEIPT",
                    receipt_id, inv_balance[pid], rcpt_time, owner_id,
                )
                # Inventory cache upsert
                await conn.execute(
                    """INSERT INTO inventory (tenant_id, product_id, quantity, updated_at)
                       VALUES ($1,$2,$3,$4)
                       ON CONFLICT (tenant_id, product_id)
                       DO UPDATE SET quantity=$3, updated_at=$4""",
                    tenant_id, pid, inv_balance[pid], rcpt_time,
                )

            total_receipts += 1

    print(f"  → {total_receipts} phiếu nhập")

    # ── Generate invoices ─────────────────────────────────────────────────
    print("Đang tạo hóa đơn bán hàng...")

    # Danh sách sản phẩm có tồn > 0 để chọn ngẫu nhiên
    def _pick_items(max_items=5) -> list[dict]:
        available = [p for p in prod_meta if inv_balance[p["id"]] > 0]
        if not available:
            return []
        n = min(len(available), random.randint(1, max_items))
        return random.sample(available, n)

    cur = START
    while cur <= END:
        n_inv = _invoices_per_day(cur)
        date_part = cur.strftime("%Y%m%d")

        for _ in range(n_inv):
            # Chọn cashier
            cashier_id = random.choices(user_ids, weights=[1, 3, 3])[0]

            # Chọn khách hàng (40% có khách, 60% vãng lai)
            if random.random() < 0.40:
                cidx = random.randrange(len(cust_ids))
                customer_id = cust_ids[cidx]
            else:
                cidx = None
                customer_id = None

            items = _pick_items(random.randint(1, 5))
            if not items:
                continue

            invoice_items = []
            subtotal = D(0)
            cost_total = D(0)
            for p in items:
                max_qty = min(int(inv_balance[p["id"]]), 10)
                if max_qty < 1:
                    continue
                qty = D(random.randint(1, max_qty))
                # Đôi khi giảm giá nhỏ
                discount = D(0)
                if random.random() < 0.05:
                    discount = roundd(p["sale"] * qty * D("0.05"))
                line_total = roundd(p["sale"] * qty - discount)
                line_cost  = roundd(p["cost"] * qty)
                subtotal  += line_total
                cost_total += line_cost
                invoice_items.append({
                    "pid": p["id"], "name": p["name"], "sku": p["sku"],
                    "unit": p["unit"], "qty": qty, "sale": p["sale"],
                    "cost": p["cost"], "discount": discount, "line_total": line_total,
                    "line_cost": line_cost,
                })

            if not invoice_items:
                continue

            total = subtotal  # no invoice-level discount for simplicity

            # Thanh toán
            method = random.choices(
                ["CASH", "BANK_TRANSFER", "MOMO"],
                weights=[65, 25, 10]
            )[0]

            # Công nợ KH: KH nằm trong DEBT_CUSTOMER_INDEXES → 20% hóa đơn bán nợ
            is_debt_invoice = (
                cidx is not None
                and cidx in DEBT_CUSTOMER_INDEXES
                and random.random() < 0.20
            )
            if is_debt_invoice:
                paid = roundd(total * D(str(random.choice(["0", "0.5", "0.7"]))))
            else:
                # Thối tiền lẻ (tiền mặt)
                if method == "CASH":
                    # Làm tròn lên 1000đ
                    paid = D(math.ceil(int(total) / 1000) * 1000)
                else:
                    paid = total

            change = max(D(0), paid - total)

            code_seq[("HD", date_part)] += 1
            code = f"HD{date_part}-{code_seq[('HD', date_part)]:03d}"

            inv_time = _rand_time(cur)
            inv_id: int = await conn.fetchval(
                """INSERT INTO invoices
                   (tenant_id, code, customer_id, cashier_id, subtotal, discount_amount,
                    total, cost_total, paid_amount, change_amount, status,
                    completed_at, created_by, created_at, updated_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                   RETURNING id""",
                tenant_id, code, customer_id, cashier_id,
                subtotal, D(0), total, cost_total, paid, change,
                "COMPLETED", inv_time, cashier_id, inv_time, inv_time,
            )

            # Payment record
            await conn.execute(
                """INSERT INTO payments
                   (invoice_id, method, amount, created_at)
                   VALUES ($1,$2,$3,$4)""",
                inv_id, method, paid, inv_time,
            )

            # Invoice items + stock movements
            for item in invoice_items:
                pid = item["pid"]
                qty = item["qty"]
                await conn.execute(
                    """INSERT INTO invoice_items
                       (invoice_id, product_id, product_name, product_sku, unit,
                        quantity, unit_price, cost_price, discount_amount, line_total)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    inv_id, pid, item["name"], item["sku"], item["unit"],
                    qty, item["sale"], item["cost"], item["discount"], item["line_total"],
                )
                inv_balance[pid] -= qty
                if inv_balance[pid] < 0:
                    inv_balance[pid] = D(0)
                await conn.execute(
                    """INSERT INTO stock_movements
                       (tenant_id, product_id, quantity, unit_cost, type, ref_type,
                        ref_id, balance_after, created_at, created_by)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                    tenant_id, pid, -qty, item["cost"], "SALE", "INVOICE",
                    inv_id, inv_balance[pid], inv_time, cashier_id,
                )
                await conn.execute(
                    """INSERT INTO inventory (tenant_id, product_id, quantity, updated_at)
                       VALUES ($1,$2,$3,$4)
                       ON CONFLICT (tenant_id, product_id)
                       DO UPDATE SET quantity=$3, updated_at=$4""",
                    tenant_id, pid, inv_balance[pid], inv_time,
                )

            # Cập nhật thống kê khách hàng
            if customer_id:
                cust_stats[customer_id]["spent"] += total
                cust_stats[customer_id]["orders"] += 1
                cust_stats[customer_id]["last_order"] = inv_time
                if is_debt_invoice:
                    total_debt_amount += (total - paid)

            total_invoices += 1

        cur += timedelta(days=1)

    print(f"  → {total_invoices} hóa đơn")

    # ── 8. Cập nhật thống kê khách hàng ─────────────────────────────────
    print("Cập nhật thống kê khách hàng...")
    for cid, stats in cust_stats.items():
        if stats["orders"] > 0:
            await conn.execute(
                """UPDATE customers
                   SET total_spent=$2, total_orders=$3, last_order_at=$4, updated_at=$5
                   WHERE id=$1""",
                cid, stats["spent"], stats["orders"], stats["last_order"],
                datetime.now(TZ),
            )

    # ── 9. Cập nhật công nợ nhà cung cấp ────────────────────────────────
    print("Cập nhật công nợ nhà cung cấp...")
    for sup_key, debt in supplier_debt.items():
        await conn.execute(
            "UPDATE suppliers SET total_debt=$2, updated_at=$3 WHERE id=$1",
            sup_id[sup_key], debt, datetime.now(TZ),
        )

    # ── 10. Cập nhật code_sequences ──────────────────────────────────────
    print("Cập nhật bảng mã số tự động...")
    for (prefix, date_part), last_num in code_seq.items():
        await conn.execute(
            """INSERT INTO code_sequences (tenant_id, prefix, date_part, last_number)
               VALUES ($1,$2,$3,$4)
               ON CONFLICT (tenant_id, prefix, date_part)
               DO UPDATE SET last_number=$4""",
            tenant_id, prefix, date_part, last_num,
        )

    # ── Tổng kết ─────────────────────────────────────────────────────────
    total_supplier_debt = sum(supplier_debt.values())
    print("\n" + "─" * 50)
    print("✅ Seed hoàn tất!")
    print(f"   Tenant id     : {tenant_id}")
    print(f"   Hóa đơn       : {total_invoices:,}")
    print(f"   Phiếu nhập    : {total_receipts}")
    print(f"   Công nợ KH    : {total_debt_amount:,.0f} đ")
    print(f"   Công nợ NCC   : {total_supplier_debt:,.0f} đ")
    print(f"   Login owner   : 0901234567 / owner123")
    print(f"   Login cashier : 0912345678 / cashier123")
    print("─" * 50)


if __name__ == "__main__":
    asyncio.run(main())
