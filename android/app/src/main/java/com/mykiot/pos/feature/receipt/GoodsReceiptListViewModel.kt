package com.mykiot.pos.feature.receipt

import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.GoodsReceiptBriefDto
import com.mykiot.pos.core.ui.paging.PageResult
import com.mykiot.pos.core.ui.paging.PagingListViewModel
import com.mykiot.pos.feature.receipt.data.ReceiptRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class GoodsReceiptListViewModel @Inject constructor(
    private val repository: ReceiptRepository,
) : PagingListViewModel<GoodsReceiptBriefDto>() {
    fun load() = refresh()
    override suspend fun fetch(page: Int): ApiResult<PageResult<GoodsReceiptBriefDto>> =
        repository.listReceipts(page)
}
