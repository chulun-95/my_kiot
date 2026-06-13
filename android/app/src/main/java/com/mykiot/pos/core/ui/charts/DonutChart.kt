package com.mykiot.pos.core.ui.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

data class DonutSlice(val label: String, val value: Double, val color: Color)

/** Donut: drawArc từng phần, lỗ giữa ~62%, animate sweep. */
@Composable
fun DonutChart(
    slices: List<DonutSlice>,
    modifier: Modifier = Modifier,
) {
    val sweeps = ChartMath.sweepAngles(slices.map { it.value })
    val anim by animateFloatAsState(
        targetValue = if (slices.isEmpty()) 0f else 1f,
        animationSpec = tween(700),
        label = "donut-anim",
    )
    Box(modifier.size(160.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.size(160.dp)) {
            val stroke = size.minDimension * 0.19f
            val inset = stroke / 2
            var start = -90f
            sweeps.forEachIndexed { i, sweep ->
                drawArc(
                    color = slices[i].color,
                    startAngle = start,
                    sweepAngle = sweep * anim,
                    useCenter = false,
                    topLeft = Offset(inset, inset),
                    size = Size(size.width - stroke, size.height - stroke),
                    style = Stroke(width = stroke),
                )
                start += sweep
            }
        }
    }
}
