package com.mykiot.pos.core.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * Giao diện đơn sắc, tối giản, hiện đại — chủ đạo đen/trắng/xám.
 * primary = đen → nút chính nền đen chữ trắng; tab active màu đen.
 */
private val MonoLight = lightColorScheme(
    primary = Ink,
    onPrimary = Paper,
    primaryContainer = PaperGrayDark,
    onPrimaryContainer = Ink,
    secondary = InkSoft,
    onSecondary = Paper,
    secondaryContainer = PaperGray,
    onSecondaryContainer = Ink,
    tertiary = Ink,
    onTertiary = Paper,
    background = Paper,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = PaperGray,
    onSurfaceVariant = InkSoft,
    surfaceContainer = Paper,
    surfaceContainerHigh = PaperGray,
    surfaceContainerHighest = PaperGrayDark,
    outline = Line,
    outlineVariant = LineSoft,
    // Giữ đơn sắc: lỗi vẫn là đen, dựa vào fill/đậm để gây chú ý
    error = Ink,
    onError = Paper,
    errorContainer = PaperGrayDark,
    onErrorContainer = Ink,
    scrim = Color(0x66000000),
)

@Composable
fun MyKiotTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = MonoLight,
        typography = MonoTypography,
        content = content,
    )
}
