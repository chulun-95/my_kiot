from backend.shared.default_categories import DEFAULT_CATEGORIES


def test_default_categories_has_21_entries():
    assert len(DEFAULT_CATEGORIES) == 21


def test_default_categories_depth_values_valid():
    for key, name, depth, parent_key in DEFAULT_CATEGORIES:
        assert depth in (1, 2)
        assert isinstance(key, str) and key
        assert isinstance(name, str) and name


def test_default_categories_parent_keys_reference_earlier_depth1():
    """Mọi parent_key (nếu có) phải trỏ tới 1 key depth=1 đã xuất hiện TRƯỚC nó trong danh
    sách — đảm bảo vòng lặp insert tuần tự trong Task 2 luôn có parent_id sẵn khi cần."""
    seen_depth1_keys: set[str] = set()
    for key, name, depth, parent_key in DEFAULT_CATEGORIES:
        if parent_key is not None:
            assert parent_key in seen_depth1_keys, (
                f"'{key}' tham chiếu parent_key='{parent_key}' chưa xuất hiện hoặc không phải depth=1"
            )
        if depth == 1:
            seen_depth1_keys.add(key)


def test_default_categories_keys_are_unique():
    keys = [key for key, *_ in DEFAULT_CATEGORIES]
    assert len(keys) == len(set(keys))
