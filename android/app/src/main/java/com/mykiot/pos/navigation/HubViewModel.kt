package com.mykiot.pos.navigation

import androidx.lifecycle.ViewModel
import com.mykiot.pos.core.auth.CurrentUser
import com.mykiot.pos.core.auth.SessionManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject

@HiltViewModel
class HubViewModel @Inject constructor(
    sessionManager: SessionManager,
) : ViewModel() {
    val user: StateFlow<CurrentUser?> = sessionManager.current
}
