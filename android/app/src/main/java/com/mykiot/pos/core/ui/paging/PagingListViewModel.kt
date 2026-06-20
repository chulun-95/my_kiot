package com.mykiot.pos.core.ui.paging

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Base ViewModel cho mọi màn danh sách có phân trang + load more.
 *
 * Lớp con chỉ cần cài đặt [fetch] để tải 1 trang. Bộ khung lo sẵn:
 * - [refresh]  : tải lại từ trang 1 (gọi khi mở màn / đổi bộ lọc / đổi từ khóa tìm).
 * - [loadMore] : nối thêm trang kế tiếp (gọi khi cuộn gần cuối danh sách).
 * - [updateItems] : sửa danh sách tại chỗ (vd: sau khi hủy 1 item) mà không tải lại.
 */
abstract class PagingListViewModel<T> : ViewModel() {

    private val _paging = MutableStateFlow(PagingState<T>())
    val paging: StateFlow<PagingState<T>> = _paging.asStateFlow()

    /** Tải 1 trang dữ liệu. [page] bắt đầu từ 1. Lớp con tự đọc từ khóa / bộ lọc của mình. */
    protected abstract suspend fun fetch(page: Int): ApiResult<PageResult<T>>

    /** Tải lại từ đầu (trang 1), giữ nguyên danh sách cũ cho tới khi có dữ liệu mới. */
    fun refresh() {
        _paging.update { it.copy(refreshing = true, error = null) }
        viewModelScope.launch {
            when (val r = fetch(1)) {
                is ApiResult.Success -> _paging.update {
                    it.copy(
                        refreshing = false,
                        items = r.data.items,
                        page = r.data.page,
                        totalPages = r.data.totalPages,
                    )
                }
                is ApiResult.Failure -> _paging.update {
                    it.copy(refreshing = false, error = r.error)
                }
            }
        }
    }

    /** Tải thêm trang kế tiếp. Tự bỏ qua nếu hết trang hoặc đang tải dở. */
    fun loadMore() {
        val s = _paging.value
        if (!s.canLoadMore) return
        _paging.update { it.copy(loadingMore = true, error = null) }
        viewModelScope.launch {
            when (val r = fetch(s.page + 1)) {
                is ApiResult.Success -> _paging.update {
                    it.copy(
                        loadingMore = false,
                        items = it.items + r.data.items,
                        page = r.data.page,
                        totalPages = r.data.totalPages,
                    )
                }
                is ApiResult.Failure -> _paging.update {
                    it.copy(loadingMore = false, error = r.error)
                }
            }
        }
    }

    /** Sửa danh sách hiện có tại chỗ (không gọi lại API). */
    protected fun updateItems(transform: (List<T>) -> List<T>) =
        _paging.update { it.copy(items = transform(it.items)) }

    /** Đặt thông báo lỗi (vd: thao tác phụ thất bại) mà không tải lại danh sách. */
    protected fun setError(error: ApiError?) = _paging.update { it.copy(error = error) }

    fun clearError() = _paging.update { it.copy(error = null) }
}
