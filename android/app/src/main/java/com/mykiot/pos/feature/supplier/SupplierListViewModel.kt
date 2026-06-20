package com.mykiot.pos.feature.supplier

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.SupplierDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
import com.mykiot.pos.feature.supplier.data.SupplierRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject

@HiltViewModel
class SupplierListViewModel @Inject constructor(
    private val repository: SupplierRepository,
) : PagingListViewModel<SupplierDto>() {

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    fun load() = refresh()

    override suspend fun fetch(page: Int): ApiResult<PageResult<SupplierDto>> =
        repository.list(_query.value.takeIf { it.isNotBlank() }, page)

    fun onQueryChange(q: String) {
        _query.value = q
        if (q.isBlank() || q.length >= 2) refresh()
    }
}
