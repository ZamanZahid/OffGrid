package com.aerogaze.app.ui

import android.graphics.BitmapFactory
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

data class LatLon(val lat: Double, val lon: Double)

private val Ocean = Color(0xFF0A1730)
private val Land = Color(0xFF24E0C8)
private val Graticule = Color(0x22A9C2FF)
private val GraticuleMain = Color(0x44A9C2FF)

/**
 * Offline world map (no network tiles). Draws the bundled equirectangular basemap tinted
 * into the constellation palette, a lat/lon graticule, and a glowing pulsing pin at the
 * solved position - plus an optional ground-truth marker and a coordinate chip.
 */
@Composable
fun WorldMap(
    position: LatLon?,
    truth: LatLon? = null,
    modifier: Modifier = Modifier,
) {
    val ctx = LocalContext.current
    val world = remember {
        fun load(name: String) = runCatching {
            ctx.assets.open(name).use { BitmapFactory.decodeStream(it).asImageBitmap() }
        }.getOrNull()
        load("basemap.jpg") ?: load("world.png")   // real continents, fall back to grid
    }
    val pulse by rememberInfiniteTransition(label = "pin").animateFloat(
        0f, 1f, infiniteRepeatable(tween(1800), RepeatMode.Restart), label = "pulse",
    )

    Box(
        modifier
            .clip(RoundedCornerShape(4.dp))
            .background(Ocean)
            .border(1.dp, GlassBorder, RoundedCornerShape(4.dp)),
    ) {
        Canvas(Modifier.fillMaxSize()) {
            // fit a 2:1 map centered
            var rw = size.width; var rh = rw / 2f
            if (rh > size.height) { rh = size.height; rw = rh * 2f }
            val left = (size.width - rw) / 2f
            val top = (size.height - rh) / 2f
            if (rw <= 0f || rh <= 0f) return@Canvas   // not laid out yet

            if (world != null) {
                drawImage(
                    image = world,
                    srcOffset = IntOffset.Zero,
                    srcSize = IntSize(world.width, world.height),
                    dstOffset = IntOffset(left.toInt(), top.toInt()),
                    dstSize = IntSize(rw.toInt(), rh.toInt()),
                )
                // darken the realistic basemap into a "night map" that fits the theme,
                // while keeping continents clearly readable
                drawRect(Color(0x99081326), topLeft = Offset(left, top), size = Size(rw, rh))
            }

            // graticule every 30°
            for (k in 0..12) {
                val x = left + rw * k / 12f
                drawLine(if (k == 6) GraticuleMain else Graticule,
                    Offset(x, top), Offset(x, top + rh), strokeWidth = if (k == 6) 1.6f else 1f)
            }
            for (k in 0..6) {
                val y = top + rh * k / 6f
                drawLine(if (k == 3) GraticuleMain else Graticule,
                    Offset(left, y), Offset(left + rw, y), strokeWidth = if (k == 3) 1.6f else 1f)
            }

            truth?.let {
                val p = project(it, left, top, rw, rh)
                drawCircle(Color(0xFF52FFB0), radius = 5f, center = p)
                drawCircle(Color(0xFF52FFB0).copy(alpha = 0.35f), radius = 11f, center = p)
            }

            position?.let {
                val p = project(it, left, top, rw, rh)
                val ringR = 10f + 26f * pulse
                drawCircle(AccentGold.copy(alpha = ((1f - pulse) * 0.6f).coerceIn(0f, 1f)), radius = ringR, center = p)
                drawCircle(AccentGold.copy(alpha = 0.18f), radius = 16f, center = p)
                drawCircle(AccentGold, radius = 6f, center = p)
                drawCircle(Color.White, radius = 2.5f, center = p)
            }
        }

        // coordinate chip
        position?.let {
            Box(
                Modifier
                    .align(Alignment.TopStart)
                    .padding(10.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(Color(0xCC0A0E26))
                    .border(1.dp, GlassBorder, RoundedCornerShape(3.dp))
                    .padding(horizontal = 10.dp, vertical = 6.dp),
            ) {
                Text(
                    "◎  ${"%.4f".format(it.lat)}, ${"%.4f".format(it.lon)}",
                    color = AccentGold,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Medium,
                    fontSize = 12.sp,
                )
            }
        }
    }
}

private fun project(p: LatLon, left: Float, top: Float, w: Float, h: Float): Offset {
    val x = left + ((p.lon + 180.0) / 360.0).toFloat() * w
    val y = top + ((90.0 - p.lat) / 180.0).toFloat() * h
    return Offset(x, y)
}
