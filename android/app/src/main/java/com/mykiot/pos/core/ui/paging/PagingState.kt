package com.mykiot.pos.core.ui.paging

import com.mykiot.pos.core.network.ApiError

/**
 * Trạng thái chung cho mọi danh sách có phân trang + load more.
 *
 * - [refreshing]  : đang tải trang đầu / làm mới (hiển thị loading toàn màn).
 * - [loadingMore] : đang tải trang kế tiếp (hiển thị spinner ở cuối danh sách).
 * - [page]        : trang đã tải gần nhất (0 = chưa tải lần nào).
 */
data class PagingState<T>(
    val items: List<T> = emptyList(),
    val page: Int = 0,
    val totalPages: Int = 1,
    val refreshing: Boolean = false,
    val loadingMore: Boolean = false,
    val error: ApiError? = null,
) {
    /** Còn trang để tải thêm và không đang tải dở. */
    val canLoadMore: Boolean
        get() = page in 1 until totalPages && !loadingMore && !refreshing

    val isEmpty: Boolean get() = items.isEmpty()
}
