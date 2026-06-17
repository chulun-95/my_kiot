package com.mykiot.pos.feature.product

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
import com.mykiot.pos.feature.product.data.ProductListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject

@HiltViewModel
class ProductListViewModel @Inject constructor(
    private val repository: ProductListRepository,
) : PagingListViewModel<ProductBriefDto>() {

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    init { refresh() }

    override suspend fun fetch(page: Int): ApiResult<PageResult<ProductBriefDto>> =
        repository.list(_query.value.takeIf { it.isNotBlank() }, page)

    fun onQueryChange(q: String) {
        _query.value = q
        if (q.isBlank() || q.length >= 2) refresh()
    }
}
