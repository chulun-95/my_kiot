package com.mykiot.pos

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalFocusManager
import com.mykiot.pos.core.auth.TokenStore
import com.mykiot.pos.core.ui.theme.MyKiotTheme
import com.mykiot.pos.navigation.AppNav
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var tokenStore: TokenStore

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val loggedIn = tokenStore.hasSession()
        setContent {
            MyKiotTheme {
                val focusManager = LocalFocusManager.current
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
                        AppNav(startLoggedIn = loggedIn)
                    }
                }
            }
        }
    }
}
