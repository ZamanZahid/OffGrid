package com.aerogaze.app

import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.aerogaze.app.ui.AccentCyan
import com.aerogaze.app.ui.AccentGold
import com.aerogaze.app.ui.GlassCard
import com.aerogaze.app.ui.GlowButton
import com.aerogaze.app.ui.LatLon
import com.aerogaze.app.ui.Space1
import com.aerogaze.app.ui.TextPrimary
import com.aerogaze.app.ui.TextSecondary
import com.aerogaze.app.ui.WorldMap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

@Composable
fun SkygazeScreen() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()

    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("") }
    var position by remember { mutableStateOf<LatLon?>(null) }
    var truth by remember { mutableStateOf<LatLon?>(null) }
    var photoPath by remember { mutableStateOf<String?>(null) }
    var uploadUri by remember { mutableStateOf<Uri?>(null) }

    fun apply(json: String, note: String?, t: LatLon?) {
        busy = false; truth = t
        val o = runCatching { JSONObject(json) }.getOrNull()
        if (o == null || !o.optBoolean("ok", false)) {
            position = null
            status = "Could not solve: ${o?.optString("error", "sky not identified") ?: "error"}\n" +
                "Need a clearer, wider shot with more naked-eye stars." + (note?.let { "\n$it" } ?: "")
            return
        }
        val lat = o.getDouble("lat"); val lon = o.getDouble("lon")
        position = LatLon(lat, lon)
        val sb = StringBuilder("POSITION  %.4f, %.4f\n".format(lat, lon))
        sb.append("stars ${o.optInt("n_stars")} · inliers ${o.optInt("n_inliers")} · resid ${o.optDouble("residual_arcsec")}\"")
        if (o.has("fov_deg")) sb.append(" · FOV ${o.optDouble("fov_deg").toInt()}°")
        t?.let { sb.append("\ntruth  %.4f, %.4f   (err %.1f km)".format(it.lat, it.lon, errKm(it.lat, it.lon, lat, lon))) }
        sb.append("\n" + (note ?: "offline · no GPS · no network"))
        status = sb.toString()
    }

    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        val path = photoPath
        if (ok && path != null) {
            busy = true; position = null; truth = null
            status = "Hold the phone at the shooting angle… reading IMU"
            scope.launch {
                val gravity = sampleGravity(ctx)
                status = "Solving your sky on-device (auto-FOV from IMU)…"
                val json = withContext(Dispatchers.IO) {
                    runCatching {
                        val (gray, w, h) = AeroGaze.bitmapToGray(CameraCapture.decodeDownsampled(path))
                        AeroGaze.solveAuto(ctx, gray, w, h, gravity)
                    }.getOrElse { "{\"ok\":false,\"error\":\"${it.message}\"}" }
                }
                apply(json, "from camera · IMU gravity · auto-FOV", null)
            }
        }
    }
    val uploadLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) uploadUri = uri
    }

    fun launchCamera() {
        val f = CameraCapture.newPhotoFile(ctx)
        photoPath = f.absolutePath
        val uri = FileProvider.getUriForFile(ctx, "${ctx.packageName}.fileprovider", f)
        runCatching { cameraLauncher.launch(uri) }
            .onFailure { status = "No camera app available: ${it.message}" }
    }

    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Text("AeroGaze", color = TextPrimary, fontSize = 30.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(18.dp))

        GlowButton("Capture & solve", { launchCamera() }, Modifier.fillMaxWidth(), enabled = !busy, primary = true)
        Spacer(Modifier.height(10.dp))
        GlowButton("Upload a photo", { uploadLauncher.launch(arrayOf("image/*")) },
            Modifier.fillMaxWidth(), enabled = !busy, primary = false)

        if (busy || status.isNotEmpty()) {
            Spacer(Modifier.height(16.dp))
            GlassCard(Modifier.fillMaxWidth()) {
                Column {
                    if (busy) {
                        CircularProgressIndicator(Modifier.height(18.dp), color = AccentCyan, strokeWidth = 2.dp)
                        Spacer(Modifier.height(8.dp))
                    }
                    Text(status, color = TextPrimary, fontSize = 13.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }

        Spacer(Modifier.height(16.dp))
        WorldMap(position, truth, Modifier.fillMaxWidth().weight(1f))
    }

    uploadUri?.let { uri ->
        UploadDialog(uri, onDismiss = { uploadUri = null }) { alt, ts ->
            uploadUri = null
            busy = true; position = null; truth = null
            status = "Solving your photo on-device (auto-FOV)…"
            scope.launch {
                val json = withContext(Dispatchers.IO) {
                    runCatching {
                        val (gray, w, h) = AeroGaze.bitmapToGray(ImagePicker.decodeDownsampled(ctx, uri))
                        AeroGaze.solveAutoHorizon(ctx, gray, w, h, alt, 0.0, ts)
                    }.getOrElse { "{\"ok\":false,\"error\":\"${it.message}\"}" }
                }
                apply(json, "angle ${alt.toInt()}° · your UTC time · quad engine", null)
            }
        }
    }
}

private suspend fun sampleGravity(ctx: Context): DoubleArray {
    val s = SkySensors(ctx); s.start()
    delay(2000)
    val g = if (s.sampleCount() > 0) s.averagedGravity() else doubleArrayOf(0.0, 0.0, -9.81)
    s.stop()
    return g
}

private fun errKm(la: Double, lo: Double, lb: Double, ob: Double): Double {
    val dlat = Math.toRadians(lb - la); val dlon = Math.toRadians(ob - lo)
    val a = sin(dlat / 2) * sin(dlat / 2) +
        cos(Math.toRadians(la)) * cos(Math.toRadians(lb)) * sin(dlon / 2) * sin(dlon / 2)
    return 6371.0 * 2 * asin(sqrt(a))
}

private val UTC_FMT: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

@Composable
private fun UploadDialog(uri: Uri, onDismiss: () -> Unit, onSolve: (Double, String) -> Unit) {
    val ctx = LocalContext.current
    val meta = remember(uri) { runCatching { ImagePicker.readMeta(ctx, uri) }.getOrNull() }
    val prefill = remember(meta) {
        meta?.timestampUtc?.let {
            runCatching { Instant.parse(it).atOffset(ZoneOffset.UTC).format(UTC_FMT) }.getOrNull()
        } ?: Instant.now().atOffset(ZoneOffset.UTC).format(UTC_FMT)
    }
    var time by remember { mutableStateOf(prefill) }
    var angle by remember { mutableStateOf("90") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Space1,
        title = { Text("Photo details", color = TextPrimary) },
        text = {
            Column {
                Text("Time taken (UTC), yyyy-MM-dd HH:mm:ss", color = TextSecondary, fontSize = 12.sp)
                OutlinedTextField(time, { time = it }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(12.dp))
                Text("Camera angle above horizon, °  (90 = straight up)", color = TextSecondary, fontSize = 12.sp)
                OutlinedTextField(angle, { angle = it }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(8.dp))
                Text("Field of view is detected automatically from the stars.",
                    color = TextSecondary, fontSize = 11.sp)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val ts = runCatching {
                    LocalDateTime.parse(time.trim(), UTC_FMT).atOffset(ZoneOffset.UTC).toInstant().toString()
                }.getOrNull()
                val alt = angle.toDoubleOrNull()?.coerceIn(0.0, 90.0) ?: 90.0
                if (ts != null) onSolve(alt, ts)
            }) { Text("Solve", color = AccentGold) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel", color = TextSecondary) } },
    )
}
