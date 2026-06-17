package com.mykiot.pos.feature.customer

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CustomerDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
import com.mykiot.pos.feature.customer.data.CustomerRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject

@HiltViewModel
class CustomerListViewModel @Inject constructor(
    private val repository: CustomerRepository,
) : PagingListViewModel<CustomerDto>() {

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    /** Giữ tên `load()` để màn hình gọi khi mở/quay lại (tải lại từ trang 1). */
    fun load() = refresh()

    override suspend fun fetch(page: Int): ApiResult<PageResult<CustomerDto>> =
        repository.list(_query.value.takeIf { it.isNotBlank() }, page)

    fun onQueryChange(q: String) {
        _query.value = q
        if (q.isBlank() || q.length >= 2) refresh()
    }
}
