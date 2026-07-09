package com.mykiot.pos

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalFocusManager
import androidx.navigation.compose.rememberNavController
import com.mykiot.pos.core.auth.AuthRepository
import com.mykiot.pos.core.auth.SessionManager
import com.mykiot.pos.core.auth.TokenStore
import com.mykiot.pos.core.ui.ExpiredOverlay
import com.mykiot.pos.core.ui.theme.MyKiotTheme
import com.mykiot.pos.navigation.AppNav
import com.mykiot.pos.navigation.Routes
import dagger.hilt.android.AndroidEntryPoint
import java.time.Instant
import javax.inject.Inject
import kotlinx.coroutines.launch

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var tokenStore: TokenStore
    @Inject lateinit var sessionManager: SessionManager
    @Inject lateinit var authRepository: AuthRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val loggedIn = tokenStore.hasSession()
        if (loggedIn) sessionManager.restore()
        setContent {
            MyKiotTheme {
                val focusManager = LocalFocusManager.current
                val navController = rememberNavController()
                val scope = rememberCoroutineScope()
                val user by sessionManager.current.collectAsState()
                val expired = user?.expiresAt?.let { it <= Instant.now() } ?: false

                Surface {
                    // Common: chạm ra vùng trống bất kỳ → ẩn bàn phím + bỏ focus.
                    // detectTapGestures chỉ nhận tap KHÔNG bị view con (nút, ô nhập) tiêu thụ,
                    // nên không ảnh hưởng các thao tác bấm/cuộn bình thường.
                    Box(
                        Modifier
                            .fillMaxSize()
                            .pointerInput(Unit) {
                                detectTapGestures(onTap = { focusManager.clearFocus() })
                            },
                    ) {
                        AppNav(navController = navController, startLoggedIn = loggedIn)
                        ExpiredOverlay(
                            visible = user != null && expired,
                            onLogout = {
                                scope.launch {
                                    authRepository.logout()
                                    navController.navigate(Routes.LOGIN) {
                                        popUpTo(0) { inclusive = true }
                                    }
                                }
                            },
                        )
                    }
                }
            }
        }
    }
}
