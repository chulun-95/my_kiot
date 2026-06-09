"""Helpers đọc tenant.settings JSONB với default app-layer.

Xem CLAUDE.md "Phần 1.5: tenants.settings JSONB — Canonical schema"
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from backend.modules.tenant.models import Tenant


# Default values khi tenant.settings không chứa key.
DEFAULTS: dict[str, Any] = {
    # POS / Bán hàng
    "allow_debt": False,
    "default_payment_method": "CASH",
    "receipt_footer": "Cám ơn quý khách!",
    # Quyền hiển thị
    "show_cost_to_cashier": False,
    "show_profit_to_cashier": False,
    # Kho
    "low_stock_threshold_default": 5,
    "negative_stock_allowed_default": False,
    # Bill / mã
    "invoice_code_prefix": "HD",
    "receipt_code_prefix": "NK",
    # Phase 2
    "tax_enabled": False,
    "tax_default_rate": 0.0,
}


def tenant_setting(tenant: Tenant | None, key: str, default: Any = None) -> Any:
    """Đọc 1 key từ tenant.settings, fallback DEFAULTS rồi default param."""
    if default is None:
        default = DEFAULTS.get(key)
    if tenant is None:
        return default
    settings = tenant.settings or {}
    return settings.get(key, default)


def can_see_cost(tenant: Tenant | None, role: str) -> bool:
    """OWNER luôn thấy giá vốn. CASHIER tuỳ tenant.settings.show_cost_to_cashier."""
    if role == "OWNER":
        return True
    return bool(tenant_setting(tenant, "show_cost_to_cashier", False))


def can_see_profit(tenant: Tenant | None, role: str) -> bool:
    """OWNER luôn thấy lợi nhuận. CASHIER tuỳ tenant.settings.show_profit_to_cashier."""
    if role == "OWNER":
        return True
    return bool(tenant_setting(tenant, "show_profit_to_cashier", False))
