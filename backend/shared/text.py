"""Text normalization helpers for diacritic-insensitive search.

The Python `vi_normalize` mirrors what Postgres `immutable_unaccent(lower(...))`
does at the DB level — strip combining marks, map đ/Đ to d/D, lowercase.
Used to normalize search queries before sending them as LIKE patterns.
"""
import unicodedata


def vi_unaccent(s: str) -> str:
    """Strip Vietnamese diacritics, preserving case. Mirrors Postgres `unaccent`."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # đ/Đ are not decomposed by NFD — handle explicitly to match Postgres unaccent.
    return s.replace("đ", "d").replace("Đ", "D")


def vi_normalize(s: str) -> str:
    return vi_unaccent(s).lower()


def vi_like_pattern(query: str) -> str:
    norm = vi_normalize(query)
    # Escape LIKE wildcards in user input so a literal % isn't treated as wildcard.
    norm = norm.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{norm}%"
