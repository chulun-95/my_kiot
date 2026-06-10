package com.mykiot.pos

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Surface
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
                Surface { AppNav(startLoggedIn = loggedIn) }
            }
        }
    }
}
