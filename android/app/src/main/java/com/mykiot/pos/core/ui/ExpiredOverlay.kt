package com.mykiot.pos.core.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.mykiot.pos.R

private const val FACEBOOK_URL = "https://www.facebook.com/profile.php?id=61579076336752"
private const val ZALO_URL = "https://zalo.me/0392368532"

/**
 * Overlay toàn màn hình chặn khi gói dịch vụ đã hết hạn. Không có nút đóng —
 * nuốt luôn nút Back cứng — chỉ thoát được qua "Đăng xuất".
 */
@Composable
fun ExpiredOverlay(visible: Boolean, onLogout: () -> Unit) {
    if (!visible) return
    BackHandler(enabled = true) {}

    val context = LocalContext.current
    fun openUrl(url: String) {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.85f)),
        contentAlignment = Alignment.Center,
    ) {
        Card(modifier = Modifier.widthIn(max = 320.dp).padding(24.dp)) {
            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text(
                    stringResource(R.string.subscription_expired_title),
                    style = MaterialTheme.typography.titleLarge,
                )
                Text(
                    stringResource(R.string.subscription_expired_message),
                    style = MaterialTheme.typography.bodyMedium,
                )
                Button(
                    onClick = { openUrl(FACEBOOK_URL) },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(stringResource(R.string.subscription_contact_facebook)) }
                Button(
                    onClick = { openUrl(ZALO_URL) },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(stringResource(R.string.subscription_contact_zalo)) }
                OutlinedButton(
                    onClick = onLogout,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text(stringResource(R.string.subscription_logout)) }
            }
        }
    }
}
