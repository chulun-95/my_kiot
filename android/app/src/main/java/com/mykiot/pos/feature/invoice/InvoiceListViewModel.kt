package com.mykiot.pos.feature.invoice

import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.InvoiceBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
open class InvoiceListViewModel @Inject constructor(
    private val repository: InvoiceListRepository,
) : PagingListViewModel<InvoiceBriefDto>() {

    /** Lớp con (vd: ReturnsViewModel) ép cứng status, vô hiệu hóa bộ lọc UI. */
    protected open val forcedStatus: String? = null

    private val _filter = MutableStateFlow(InvoiceFilter.ALL)
    val filter: StateFlow<InvoiceFilter> = _filter.asStateFlow()

    private val _search = MutableStateFlow("")
    val search: StateFlow<String> = _search.asStateFlow()

    /** Khoảng ngày lọc (ISO "YYYY-MM-DD") — null nghĩa là không lọc. */
    private val _dateFrom = MutableStateFlow<String?>(null)
    val dateFrom: StateFlow<String?> = _dateFrom.asStateFlow()
    private val _dateTo = MutableStateFlow<String?>(null)
    val dateTo: StateFlow<String?> = _dateTo.asStateFlow()

    private val _cancelingId = MutableStateFlow<Long?>(null)
    val cancelingId: StateFlow<Long?> = _cancelingId.asStateFlow()

    fun load() = refresh()

    override suspend fun fetch(page: Int): ApiResult<PageResult<InvoiceBriefDto>> =
        repository.list(
            status = forcedStatus ?: _filter.value.toStatus(),
            search = _search.value.takeIf { it.isNotBlank() },
            from = _dateFrom.value,
            to = _dateTo.value,
            page = page,
        )

    fun setFilter(f: InvoiceFilter) {
        if (forcedStatus != null || _filter.value == f) return
        _filter.value = f
        refresh()
    }

    /** Tìm theo mã HĐ / tên / SĐT khách. Refresh khi xóa trắng hoặc nhập ≥ 2 ký tự. */
    fun onSearchChange(q: String) {
        _search.value = q
        if (q.isBlank() || q.trim().length >= 2) refresh()
    }

    /** Đặt khoảng ngày lọc (null,null = bỏ lọc) rồi tải lại. */
    fun setDateRange(from: String?, to: String?) {
        _dateFrom.value = from
        _dateTo.value = to
        refresh()
    }

    fun clearDateRange() = setDateRange(null, null)

    fun requestCancel(id: Long) { _cancelingId.value = id }

    fun dismissCancel() { _cancelingId.value = null }

    fun cancelInvoice(id: Long, reason: String) {
        _cancelingId.value = null
        viewModelScope.launch {
            when (val r = repository.cancel(id, reason)) {
                is ApiResult.Success ->
                    updateItems { items -> items.map { if (it.id == id) it.copy(status = "CANCELLED") else it } }
                is ApiResult.Failure -> setError(r.error)
            }
        }
    }
}
