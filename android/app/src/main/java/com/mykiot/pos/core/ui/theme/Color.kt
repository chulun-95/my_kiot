package com.mykiot.pos.core.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * Bảng màu ĐƠN SẮC theo thang slate (đồng nhất với web slate-900/slate-50).
 * Điểm nhấn dùng độ đậm/fill. MÀU chỉ xuất hiện trong biểu đồ (Data* bên dưới).
 */
val Ink = Color(0xFF0F172A)          // slate-900 — chữ chính, primary, series chart chính
val InkSoft = Color(0xFF64748B)      // slate-500 — chữ phụ, icon mờ
val Paper = Color(0xFFFFFFFF)        // surface
val PaperGray = Color(0xFFF8FAFC)    // slate-50 — nền app
val PaperGrayDark = Color(0xFFF1F5F9)// slate-100 — fill nhẹ/chip
val Line = Color(0xFFE2E8F0)         // slate-200 — viền/divider
val LineSoft = Color(0xFFEEF2F6)     // viền rất nhạt

// ---- Màu DỮ LIỆU: chỉ dùng trong biểu đồ ----
val DataInk = Color(0xFF0F172A)      // series chính (doanh thu, top SP) — khớp web #0f172a
val DataProfit = Color(0xFF16A34A)   // lợi nhuận / dương — khớp web #16a34a
val DataCash = Color(0xFF16A34A)     // CASH
val DataBank = Color(0xFF0EA5E9)     // BANK_TRANSFER (sky)
val DataWallet = Color(0xFF8B5CF6)   // MOMO / ví (violet)
val DataOther = Color(0xFFF59E0B)    // khác (amber)
val DataWarn = Color(0xFFF59E0B)     // cảnh báo (hàng sắp hết)
