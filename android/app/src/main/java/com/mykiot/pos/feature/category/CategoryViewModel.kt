package com.mykiot.pos.feature.category

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.mykiot.pos.core.network.ApiResult
import com.mykiot.pos.core.network.dto.CategoryCreateDto
import com.mykiot.pos.feature.category.data.CategoryRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CategoryViewModel @Inject constructor(
    private val repository: CategoryRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(CategoryUiState())
    val state: StateFlow<CategoryUiState> = _state.asStateFlow()

    fun load() {
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            when (val r = repository.tree()) {
                is ApiResult.Success -> _state.update { it.copy(loading = false, nodes = r.data) }
                is ApiResult.Failure -> _state.update { it.copy(loading = false, error = r.error) }
            }
        }
    }

    fun openAdd(parentId: Long?) =
        _state.update { it.copy(editorOpen = true, editorParentId = parentId, editorEditingId = null, editorName = "") }

    fun openEdit(id: Long, name: String) =
        _state.update { it.copy(editorOpen = true, editorEditingId = id, editorParentId = null, editorName = name) }

    fun onEditorName(v: String) = _state.update { it.copy(editorName = v) }
    fun closeEditor() = _state.update { it.copy(editorOpen = false, editorName = "") }
    fun clearError() = _state.update { it.copy(error = null) }

    fun saveEditor() {
        val s = _state.value
        if (s.editorName.isBlank()) return
        viewModelScope.launch {
            val body = CategoryCreateDto(name = s.editorName.trim(), parentId = s.editorParentId)
            val editId = s.editorEditingId
            val r = if (editId != null) repository.update(editId, body) else repository.create(body)
            when (r) {
                is ApiResult.Success -> { _state.update { it.copy(editorOpen = false, editorName = "") }; load() }
                is ApiResult.Failure -> _state.update { it.copy(error = r.error) }
            }
        }
    }

    fun delete(id: Long) {
        viewModelScope.launch {
            when (val r = repository.delete(id)) {
                is ApiResult.Success -> load()
                is ApiResult.Failure -> _state.update { it.copy(error = r.error) }
            }
        }
    }
}
