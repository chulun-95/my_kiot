package com.mykiot.pos.core.ui.charts

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.mykiot.pos.core.ui.theme.DataInk

/** Thanh ngang top-N: tên + thanh tỉ lệ + giá trị. */
@Composable
fun HBarChart(
    data: List<Pair<String, Double>>,
    valueLabel: (Double) -> String,
    modifier: Modifier = Modifier,
    barColor: Color = DataInk,
) {
    val fractions = ChartMath.normalize(data.map { it.second })
    val anim by animateFloatAsState(
        targetValue = if (data.isEmpty()) 0f else 1f,
        animationSpec = tween(700),
        label = "hbar-anim",
    )
    Column(modifier.fillMaxWidth()) {
        data.forEachIndexed { i, (label, value) ->
            Row(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                Text(
                    label,
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    modifier = Modifier.weight(0.42f),
                )
                Box(Modifier.weight(0.58f)) {
                    Box(
                        Modifier
                            .fillMaxWidth(fractions[i] * anim)
                            .height(18.dp)
                            .clip(RoundedCornerShape(6.dp))
                            .background(barColor),
                    )
                }
            }
            Text(
                valueLabel(value),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 4.dp),
            )
            Spacer(Modifier.height(2.dp))
        }
    }
}
