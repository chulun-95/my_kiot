package com.mykiot.pos.core.ui.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.theme.DataInk

/**
 * Cột dọc đơn giản: nhãn trục X dưới mỗi cột, animate chiều cao khi vào.
 * Có thể bấm chọn từng cột: [onBarClick] nhận index; [selectedIndex] làm nổi bật cột đang chọn.
 */
@Composable
fun ColumnChart(
    data: List<Pair<String, Double>>,
    modifier: Modifier = Modifier,
    barColor: Color = DataInk,
    selectedIndex: Int? = null,
    onBarClick: ((Int) -> Unit)? = null,
) {
    val fractions = ChartMath.normalize(data.map { it.second })
    val anim by animateFloatAsState(
        targetValue = if (data.isEmpty()) 0f else 1f,
        animationSpec = tween(700),
        label = "col-anim",
    )
    val dimColor = barColor.copy(alpha = 0.30f)
    Column(modifier.fillMaxWidth()) {
        Canvas(
            Modifier
                .fillMaxWidth()
                .height(160.dp)
                .padding(top = 4.dp)
                .then(
                    if (onBarClick != null && data.isNotEmpty()) {
                        Modifier.pointerInput(data.size) {
                            detectTapGestures { offset ->
                                val n = data.size
                                val gap = size.width * 0.04f
                                val barW = (size.width - gap * (n - 1)) / n
                                val idx = (offset.x / (barW + gap)).toInt().coerceIn(0, n - 1)
                                onBarClick(idx)
                            }
                        }
                    } else Modifier,
                ),
        ) {
            if (data.isEmpty()) return@Canvas
            val n = data.size
            val gap = size.width * 0.04f
            val barW = (size.width - gap * (n - 1)) / n
            fractions.forEachIndexed { i, f ->
                val h = size.height * f * anim
                val x = i * (barW + gap)
                val color = if (selectedIndex == null || selectedIndex == i) barColor else dimColor
                drawRect(
                    color = color,
                    topLeft = Offset(x, size.height - h),
                    size = Size(barW, h),
                )
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 6.dp)) {
            data.forEachIndexed { i, (label, _) ->
                val selected = selectedIndex == i
                Text(
                    label,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal,
                    color = if (selected) MaterialTheme.colorScheme.onSurface
                    else MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
