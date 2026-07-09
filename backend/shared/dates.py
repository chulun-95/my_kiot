"""Date helpers không phụ thuộc thư viện ngoài (không có python-dateutil)."""
from __future__ import annotations

import calendar
from datetime import datetime


def add_months(dt: datetime, months: int) -> datetime:
    """Cộng `months` tháng vào `dt`, xử lý rollover năm và clamp ngày cuối tháng.

    Ví dụ: 31/01 + 1 tháng → 28/02 (hoặc 29/02 năm nhuận), không lỗi ValueError
    như khi cộng thẳng timedelta hay gọi replace(month=...) với ngày không tồn tại.
    """
    total_month_index = dt.month - 1 + months
    year = dt.year + total_month_index // 12
    month = total_month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)
