package com.aerogaze.app.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.cos
import kotlin.math.sin
import kotlin.random.Random

// ---- Palette: deep space + starlight -------------------------------------- //
val Space0 = Color(0xFF05061A)
val Space1 = Color(0xFF090B26)
val Space2 = Color(0xFF0E1233)
val StarColor = Color(0xFFEAF1FF)
val AccentCyan = Color(0xFF67E8F9)
val AccentViolet = Color(0xFFA78BFA)
val AccentGold = Color(0xFFFFD27D)
val TextPrimary = Color(0xFFE7ECFF)
val TextSecondary = Color(0xFF8C95C9)
val GlassBg = Color(0x14B9C6FF)
val GlassBorder = Color(0x33A9B8FF)
val Nebula1 = Color(0x335B6CFF)
val Nebula2 = Color(0x2622D3C7)
val ConstLine = Color(0x3A9FB4FF)

// Corner radii: barely rounded, almost square.
private val CardCorner = RoundedCornerShape(3.dp)
private val ButtonCorner = RoundedCornerShape(3.dp)

@Composable
fun ConstellationTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = AccentCyan,
            secondary = AccentViolet,
            background = Space0,
            surface = Space1,
            onPrimary = Space0,
            onBackground = TextPrimary,
            onSurface = TextPrimary,
            error = Color(0xFFFF6B6B),
        ),
        content = content,
    )
}

private class Star(val x: Float, val y: Float, val r: Float, val phase: Float, val spd: Float)
private class Meteor(val x0: Float, val y0: Float, val dx: Float, val dy: Float, val len: Float, val phase: Float)

/**
 * A real asterism: points in a uniform unit space (x right, y down) drawn at one scale
 * for BOTH axes, so the shape never stretches with the screen's aspect ratio. `ax`/`ay`
 * are the anchor as a fraction of the canvas; `scale` is a fraction of canvas width.
 */
private class Constellation(
    val ax: Float, val ay: Float, val scale: Float,
    val pts: List<Offset>, val edges: List<Pair<Int, Int>>,
)

private val CONSTELLATIONS = listOf(
    // Big Dipper (bowl + handle)
    Constellation(0.55f, 0.10f, 0.105f,
        listOf(
            Offset(1.90f, 0.00f), Offset(1.95f, 0.55f), Offset(1.25f, 0.60f), Offset(1.30f, 0.15f),
            Offset(0.85f, 0.20f), Offset(0.45f, 0.35f), Offset(0.00f, 0.55f),
        ),
        listOf(0 to 1, 1 to 2, 2 to 3, 3 to 0, 3 to 4, 4 to 5, 5 to 6)),
    // Cassiopeia (W)
    Constellation(0.10f, 0.27f, 0.095f,
        listOf(
            Offset(0.0f, 0.0f), Offset(0.5f, 0.5f), Offset(1.0f, 0.1f), Offset(1.5f, 0.55f), Offset(2.0f, 0.15f),
        ),
        listOf(0 to 1, 1 to 2, 2 to 3, 3 to 4)),
    // Orion (shoulders, belt, feet)
    Constellation(0.66f, 0.58f, 0.115f,
        listOf(
            Offset(0.00f, 0.00f), Offset(0.95f, 0.05f), Offset(0.30f, 0.80f), Offset(0.52f, 0.88f),
            Offset(0.74f, 0.95f), Offset(0.18f, 1.60f), Offset(0.98f, 1.55f),
        ),
        listOf(0 to 1, 0 to 2, 1 to 4, 2 to 3, 3 to 4, 2 to 5, 4 to 6)),
)

/**
 * Living deep-space backdrop: gradient + breathing nebulae + a gently swaying, twinkling
 * starfield, real constellation shapes, and periodic shooting stars.
 */
@Composable
fun ConstellationBackground(
    modifier: Modifier = Modifier,
    content: @Composable BoxScope.() -> Unit,
) {
    val stars = remember {
        val rng = Random(7)
        List(150) {
            Star(rng.nextFloat(), rng.nextFloat(), rng.nextFloat() * 1.7f + 0.5f,
                rng.nextFloat() * 6.2832f, rng.nextFloat() * 0.8f + 0.3f)
        }
    }
    val meteors = remember {
        listOf(
            Meteor(0.05f, 0.06f, 0.55f, 0.40f, 0.16f, 0.00f),
            Meteor(0.80f, 0.02f, -0.50f, 0.42f, 0.15f, 0.42f),
            Meteor(0.40f, 0.14f, 0.50f, 0.30f, 0.13f, 0.76f),
        )
    }

    val t = rememberInfiniteTransition(label = "sky")
    val twinkle by t.animateFloat(0f, 6.2832f,
        infiniteRepeatable(tween(11000, easing = LinearEasing), RepeatMode.Restart), label = "twinkle")
    val sway by t.animateFloat(0f, 6.2832f,
        infiniteRepeatable(tween(24000, easing = LinearEasing), RepeatMode.Restart), label = "sway")
    val meteorT by t.animateFloat(0f, 1f,
        infiniteRepeatable(tween(6500, easing = LinearEasing), RepeatMode.Restart), label = "meteor")
    val pulse by t.animateFloat(0f, 1f,
        infiniteRepeatable(tween(7000, easing = LinearEasing), RepeatMode.Reverse), label = "pulse")

    Box(
        modifier
            .fillMaxSize()
            .background(Brush.verticalGradient(listOf(Space0, Space1, Space2)))
    ) {
        Canvas(Modifier.fillMaxSize()) {
            if (size.minDimension <= 0f) return@Canvas   // avoid 0-radius gradients
            val sx = sin(sway) * 7f
            val sy = cos(sway * 0.8f) * 5f

            // breathing nebulae
            val nr1 = size.minDimension * (0.62f + 0.10f * pulse)
            val nr2 = size.minDimension * (0.72f - 0.08f * pulse)
            val c1 = Offset(size.width * 0.18f, size.height * 0.12f)
            val c2 = Offset(size.width * 0.85f, size.height * 0.82f)
            drawCircle(Brush.radialGradient(listOf(Nebula1, Color.Transparent), c1, nr1), nr1, c1)
            drawCircle(Brush.radialGradient(listOf(Nebula2, Color.Transparent), c2, nr2), nr2, c2)

            // real constellation shapes (uniform scale on both axes => no stretching)
            CONSTELLATIONS.forEach { c ->
                val ox = c.ax * size.width + sx
                val oy = c.ay * size.height + sy
                val sc = size.width * c.scale
                fun cp(i: Int) = Offset(ox + c.pts[i].x * sc, oy + c.pts[i].y * sc)
                c.edges.forEach { (a, b) -> drawLine(ConstLine, cp(a), cp(b), strokeWidth = 1.3f) }
                c.pts.indices.forEach { i ->
                    val tw = (0.6f + 0.4f * sin(twinkle * 0.7f + i)).coerceIn(0.35f, 1f)
                    drawCircle(StarColor.copy(alpha = tw), radius = 2.0f, center = cp(i))
                }
            }

            // twinkling background starfield
            stars.forEach { s ->
                val tw = (0.55f + 0.45f * sin(twinkle * s.spd + s.phase)).coerceIn(0.12f, 1f)
                drawCircle(StarColor.copy(alpha = tw), radius = s.r,
                    center = Offset(s.x * size.width + sx, s.y * size.height + sy))
            }

            // shooting stars
            meteors.forEach { m ->
                val local = (meteorT + m.phase) % 1f
                val window = 0.16f
                if (local < window) {
                    val p = local / window
                    val fade = sin(p * 3.1416f).coerceIn(0f, 1f)   // never negative (alpha must be >= 0)
                    val head = Offset((m.x0 + m.dx * p) * size.width, (m.y0 + m.dy * p) * size.height)
                    val tail = Offset(head.x - m.dx * m.len * size.width, head.y - m.dy * m.len * size.height)
                    drawLine(
                        Brush.linearGradient(
                            listOf(StarColor.copy(alpha = 0.9f * fade), Color.Transparent),
                            start = head, end = tail),
                        head, tail, strokeWidth = 3f, cap = StrokeCap.Round)
                    drawCircle(StarColor.copy(alpha = fade), radius = 2.6f, center = head)
                }
            }
        }
        content()
    }
}

/** Frosted-glass panel. */
@Composable
fun GlassCard(modifier: Modifier = Modifier, content: @Composable BoxScope.() -> Unit) {
    Box(
        modifier
            .clip(CardCorner)
            .background(GlassBg)
            .border(1.dp, GlassBorder, CardCorner)
            .padding(16.dp),
        content = content,
    )
}

/** Glowing action button. `primary` = filled gradient; else a subtle glass button. */
@Composable
fun GlowButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    primary: Boolean = true,
) {
    // Appearance stays IDENTICAL whether enabled or not; disabled only dims uniformly,
    // so buttons never change fill/border (e.g. while a solve is running).
    val bg = if (primary) Brush.horizontalGradient(listOf(AccentCyan, AccentViolet)) else SolidColor(GlassBg)
    val borderColor = if (primary) AccentCyan.copy(alpha = 0.55f) else GlassBorder
    Box(
        modifier
            .clip(ButtonCorner)
            .alpha(if (enabled) 1f else 0.5f)
            .background(bg)
            .border(1.dp, borderColor, ButtonCorner)
            .clickable(enabled = enabled) { onClick() }
            .padding(vertical = 15.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text,
            color = if (primary) Space0 else TextPrimary,
            fontWeight = FontWeight.SemiBold,
            fontSize = 15.sp,
            textAlign = TextAlign.Center,
        )
    }
}

/** Small section / overline label. */
@Composable
fun Overline(text: String, modifier: Modifier = Modifier) {
    Text(
        text.uppercase(),
        modifier = modifier.fillMaxWidth(),
        color = TextSecondary,
        fontSize = 11.sp,
        letterSpacing = 2.sp,
        fontWeight = FontWeight.Medium,
    )
}
