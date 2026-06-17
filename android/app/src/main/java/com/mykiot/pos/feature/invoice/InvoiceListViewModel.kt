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

    private val _cancelingId = MutableStateFlow<Long?>(null)
    val cancelingId: StateFlow<Long?> = _cancelingId.asStateFlow()

    fun load() = refresh()

    override suspend fun fetch(page: Int): ApiResult<PageResult<InvoiceBriefDto>> =
        repository.list(status = forcedStatus ?: _filter.value.toStatus(), page = page)

    fun setFilter(f: InvoiceFilter) {
        if (forcedStatus != null || _filter.value == f) return
        _filter.value = f
        refresh()
    }

    fun requestCancel(id: Long) { _cancelingId.value = id }

    fun dismissCancel() { _cancelingId.value = null }

    fun cancelInvoice(id: Long, reason: String) {
        _cancelingId.value = null
        viewModelScope.launch {
            when (val r = repository.cancel(id, reason)) {
                is ApiResult.Success ->
                    updateItems { items -> items.map { if (it.id == id) it.copy(status = "CANCELLED") else it } }
                is ApiResult.Failure -> setError(r.error.message)
            }
        }
    }
}
