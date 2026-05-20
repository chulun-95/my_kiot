import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.config import settings


PHONE_REGEX = re.compile(r"^(0[3|5|7|8|9])[0-9]{8}$")


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_REGEX.match(phone or ""))


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, tenant_id: int, role: str) -> str:
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "tid": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)


def refresh_token_expiry() -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )


def slugify(value: str) -> str:
    value = value.replace("đ", "d").replace("Đ", "D")
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value or "shop"


def random_slug_suffix(n: int = 4) -> str:
    return secrets.token_hex(n // 2 if n % 2 == 0 else (n + 1) // 2)[:n]
