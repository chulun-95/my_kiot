package com.mykiot.pos.core.ui.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.theme.DataInk

/** Cột dọc đơn giản: nhãn trục X dưới mỗi cột, animate chiều cao khi vào. */
@Composable
fun ColumnChart(
    data: List<Pair<String, Double>>,
    modifier: Modifier = Modifier,
    barColor: Color = DataInk,
) {
    val fractions = ChartMath.normalize(data.map { it.second })
    val anim by animateFloatAsState(
        targetValue = if (data.isEmpty()) 0f else 1f,
        animationSpec = tween(700),
        label = "col-anim",
    )
    Column(modifier.fillMaxWidth()) {
        Canvas(
            Modifier
                .fillMaxWidth()
                .height(160.dp)
                .padding(top = 4.dp),
        ) {
            if (data.isEmpty()) return@Canvas
            val n = data.size
            val gap = size.width * 0.04f
            val barW = (size.width - gap * (n - 1)) / n
            fractions.forEachIndexed { i, f ->
                val h = size.height * f * anim
                val x = i * (barW + gap)
                drawRect(
                    color = barColor,
                    topLeft = Offset(x, size.height - h),
                    size = Size(barW, h),
                )
            }
        }
        Row(Modifier.fillMaxWidth().padding(top = 6.dp)) {
            data.forEach { (label, _) ->
                Text(
                    label,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
