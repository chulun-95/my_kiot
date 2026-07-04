package com.mykiot.pos.feature.product

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.R
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.i18n.ResProvider
import com.mykiot.pos.core.network.ApiError
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CategoryNodeDto
import com.mykiot.pos.core.network.dto.ProductBriefDto
import com.mykiot.pos.core.network.dto.ProductCreateDto
import com.mykiot.pos.core.network.dto.ProductUpdateDto
import com.mykiot.pos.feature.category.data.CategoryRepository
import com.mykiot.pos.feature.product.data.ProductRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.math.BigDecimal
import javax.inject.Inject

data class CategoryOption(val id: Long, val label: String)

data class AddProductUiState(
    val name: String = "",
    val barcode: String = "",
    val sku: String = "",
    val unit: String = "cái",
    val costPrice: String = "",
    val salePrice: String = "",
    val minStock: String = "0",
    val status: String = "ACTIVE",
    val categoryId: Long? = null,
    val categoryLabel: String = "",
    val categories: List<CategoryOption> = emptyList(),
    val isOwner: Boolean = false,
    val editingId: Long? = null,
    val loading: Boolean = false,
    val error: ApiError? = null,
    val created: ProductBriefDto? = null,
    val saved: Boolean = false,
)

@HiltViewModel
class AddProductViewModel @Inject constructor(
    private val repository: ProductRepository,
    private val categoryRepository: CategoryRepository,
    private val sessionManager: SessionManager,
    private val res: ResProvider,
) : ViewModel() {

    private val _state = MutableStateFlow(AddProductUiState(isOwner = sessionManager.isOwner))
    val state: StateFlow<AddProductUiState> = _state.asStateFlow()

    private var prefilled = false
    private var categoriesLoaded = false

    fun prefillBarcode(barcode: String) {
        if (prefilled) return
        prefilled = true
        if (barcode.isNotBlank()) _state.update { it.copy(barcode = barcode) }
    }

    fun loadCategories() {
        if (categoriesLoaded) return
        categoriesLoaded = true
        viewModelScope.launch {
            when (val r = categoryRepository.tree()) {
                is ApiResult.Success -> {
                    // `startEdit` và `loadCategories` chạy song song (2 LaunchedEffect độc lập ở
                    // Composable) — nếu categoryId đã có trước khi list nhóm hàng về, backfill lại
                    // label ở đây để không bị kẹt ở "Không có nhóm" khi thực ra đã có category_id.
                    val options = flattenCategories(r.data)
                    _state.update { current ->
                        current.copy(
                            categories = options,
                            categoryLabel = options.find { it.id == current.categoryId }?.label ?: current.categoryLabel,
                        )
                    }
                }
                is ApiResult.Failure -> Unit // Không chặn form nếu tải nhóm hàng lỗi
            }
        }
    }

    fun startEdit(id: Long) {
        if (_state.value.editingId == id) return
        _state.update { it.copy(editingId = id, loading = true) }
        viewModelScope.launch {
            when (val r = repository.get(id)) {
                is ApiResult.Success -> {
                    val p = r.data
                    _state.update { current ->
                        current.copy(
                            loading = false,
                            name = p.name,
                            barcode = p.barcode ?: "",
                            sku = p.sku,
                            unit = p.unit,
                            costPrice = p.costPrice?.toLong()?.toString() ?: "",
                            salePrice = p.salePrice.toLong().toString(),
                            minStock = p.minStock.toString(),
                            status = p.status,
                            categoryId = p.categoryId,
                            categoryLabel = current.categories.find { it.id == p.categoryId }?.label ?: "",
                        )
                    }
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun onName(v: String) = _state.update { it.copy(name = v) }
    fun onBarcode(v: String) = _state.update { it.copy(barcode = v) }
    fun onSku(v: String) = _state.update { it.copy(sku = v) }
    fun onUnit(v: String) = _state.update { it.copy(unit = v) }
    fun onCost(v: String) = _state.update { it.copy(costPrice = v) }
    fun onSale(v: String) = _state.update { it.copy(salePrice = v) }
    fun onMinStock(v: String) = _state.update { it.copy(minStock = v) }
    fun onStatus(v: String) = _state.update { it.copy(status = v) }
    fun onCategory(id: Long?, label: String) = _state.update { it.copy(categoryId = id, categoryLabel = label) }
    fun clearError() = _state.update { it.copy(error = null) }

    private fun normalizePrice(v: String): String? {
        val t = v.trim().replace(",", "")
        if (t.isBlank()) return "0"
        return try { BigDecimal(t); t } catch (_: Exception) { null }
    }

    fun submit() {
        val s = _state.value
        if (s.name.isBlank()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_name_required))) }
            return
        }
        if (s.unit.isBlank()) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_unit_required))) }
            return
        }
        val cost = normalizePrice(s.costPrice)
        val sale = normalizePrice(s.salePrice)
        if (cost == null || sale == null) {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_price_invalid))) }
            return
        }
        if (sale == "0") {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_sale_price_required))) }
            return
        }
        if (s.isOwner && cost == "0") {
            _state.update { it.copy(error = ApiError("VALIDATION", res.get(R.string.cat_product_err_cost_price_required))) }
            return
        }
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            val editId = s.editingId
            val trimmedName = s.name.trim()
            val trimmedSku = s.sku.trim().ifBlank { null }
            val trimmedBarcode = s.barcode.trim().ifBlank { null }
            val trimmedUnit = s.unit.trim().ifBlank { "cái" }
            val minStock = s.minStock.toIntOrNull() ?: 0
            val result = if (editId != null) {
                repository.update(
                    editId,
                    ProductUpdateDto(
                        name = trimmedName,
                        sku = trimmedSku,
                        barcode = trimmedBarcode,
                        categoryId = s.categoryId,
                        unit = trimmedUnit,
                        costPrice = if (s.isOwner) cost else null,
                        salePrice = sale,
                        minStock = minStock,
                        status = s.status,
                    ),
                )
            } else {
                repository.create(
                    ProductCreateDto(
                        name = trimmedName,
                        sku = trimmedSku,
                        barcode = trimmedBarcode,
                        categoryId = s.categoryId,
                        unit = trimmedUnit,
                        costPrice = cost,
                        salePrice = sale,
                        minStock = minStock,
                        status = s.status,
                    ),
                )
            }
            when (result) {
                is ApiResult.Success -> {
                    val createdDto = if (editId == null) result.data else null
                    _state.update { it.copy(loading = false, saved = true, created = createdDto) }
                }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = result.error) }
            }
        }
    }
}

private fun flattenCategories(nodes: List<CategoryNodeDto>, depth: Int = 0): List<CategoryOption> {
    val out = mutableListOf<CategoryOption>()
    for (n in nodes) {
        out += CategoryOption(n.id, "— ".repeat(depth) + n.name)
        if (n.children.isNotEmpty()) out += flattenCategories(n.children, depth + 1)
    }
    return out
}
