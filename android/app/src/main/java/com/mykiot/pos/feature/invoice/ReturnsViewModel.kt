package com.mykiot.pos.feature.invoice

import com.mykiot.pos.feature.invoice.data.InvoiceListRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class ReturnsViewModel @Inject constructor(
    repository: InvoiceListRepository,
) : InvoiceListViewModel(repository) {
    override val loadStatus: String = "COMPLETED"
}
