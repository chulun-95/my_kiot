package com.mykiot.pos.core.ui.paging

import com.mykiot.pos.core.network.dto.PaginationDto

/**
 * Kết quả 1 trang dữ liệu trả về từ repository.
 * [page] bắt đầu từ 1; [totalPages] tối thiểu là 1.
 */
data class PageResult<T>(
    val items: List<T>,
    val page: Int,
    val totalPages: Int,
) {
    companion object {
        /** Tạo PageResult từ response chuẩn { items, pagination }. */
        fun <T> from(items: List<T>, pagination: PaginationDto?): PageResult<T> =
            PageResult(
                items = items,
                page = pagination?.page ?: 1,
                totalPages = (pagination?.totalPages ?: 1).coerceAtLeast(1),
            )
    }
}
