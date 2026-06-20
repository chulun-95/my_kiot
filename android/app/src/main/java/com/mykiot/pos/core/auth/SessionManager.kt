package com.mykiot.pos.core.auth

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Nguồn sự thật in-memory về user/role của phiên hiện tại.
 * Persist nằm ở [TokenStore]; [restore] nạp lại khi cold-start.
 */
@Singleton
class SessionManager @Inject constructor(
    private val tokenStore: TokenStore,
) {
    private val _current = MutableStateFlow<CurrentUser?>(null)
    val current: StateFlow<CurrentUser?> = _current.asStateFlow()

    val isOwner: Boolean get() = _current.value?.role == "OWNER"

    fun set(user: CurrentUser) { _current.value = user }
    fun clear() { _current.value = null }
    fun restore() { _current.value = tokenStore.getUser() }
}
