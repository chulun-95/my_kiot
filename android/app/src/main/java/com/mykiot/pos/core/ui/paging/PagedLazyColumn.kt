package com.mykiot.pos.core.ui.paging

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.flow.distinctUntilChanged

/**
 * Base ListView dùng chung cho mọi màn danh sách: một [LazyColumn] đã tích hợp sẵn
 * infinite-scroll load more, spinner ở cuối khi tải thêm, và empty state.
 *
 * Khi người dùng cuộn tới gần cuối (còn [prefetchDistance] item) thì tự gọi [onLoadMore].
 *
 * @param state    trạng thái phân trang (từ [PagingListViewModel.paging]).
 * @param onLoadMore callback tải thêm trang kế (thường là `viewModel::loadMore`).
 * @param key      khóa ổn định cho mỗi item (giúp Compose tái sử dụng & giữ vị trí cuộn).
 * @param item     composable render 1 dòng.
 */
@Composable
fun <T> PagedLazyColumn(
    state: PagingState<T>,
    onLoadMore: () -> Unit,
    modifier: Modifier = Modifier,
    listState: LazyListState = rememberLazyListState(),
    key: ((T) -> Any)? = null,
    emptyText: String = "Chưa có dữ liệu",
    prefetchDistance: Int = 4,
    item: @Composable (T) -> Unit,
) {
    // Theo dõi vị trí cuộn → tự load more khi gần chạm đáy.
    LaunchedEffect(listState, state.canLoadMore) {
        snapshotFlowLastVisible(listState)
            .distinctUntilChanged()
            .collect { (lastVisible, total) ->
                if (state.canLoadMore && total > 0 && lastVisible >= total - 1 - prefetchDistance) {
                    onLoadMore()
                }
            }
    }

    if (state.isEmpty && !state.refreshing) {
        Text(
            emptyText,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(vertical = 16.dp),
        )
        return
    }

    LazyColumn(state = listState, modifier = modifier.fillMaxSize()) {
        items(state.items, key = key) { item(it) }

        if (state.loadingMore) {
            item(key = "__paging_loading_more__") {
                Box(
                    Modifier
                        .fillMaxWidth()
                        .padding(vertical = 16.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(28.dp),
                        color = MaterialTheme.colorScheme.onSurface,
                        strokeWidth = 2.5.dp,
                    )
                }
            }
        }
    }
}

private fun snapshotFlowLastVisible(listState: LazyListState) =
    androidx.compose.runtime.snapshotFlow {
        val layout = listState.layoutInfo
        val lastVisible = layout.visibleItemsInfo.lastOrNull()?.index ?: -1
        lastVisible to layout.totalItemsCount
    }
