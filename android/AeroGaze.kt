package com.example.aerogaze

import android.content.Context
import android.graphics.Bitmap
import android.hardware.camera2.CameraCharacteristics
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import java.io.File
import java.time.Instant
import kotlin.math.atan
import kotlin.math.roundToInt

/**
 * Thin Kotlin wrapper over the AeroGaze Python engine (Chaquopy).
 *
 * Kotlin supplies pixels + gravity + clock; Python returns a JSON position string.
 * No network is used anywhere.
 */
object AeroGaze {

    private fun module(name: String): PyObject = Python.getInstance().getModule(name)

    /** Copy a bundled asset to filesDir (np.load needs a real path) and return it. */
    fun copyAsset(context: Context, name: String): String {
        val out = File(context.filesDir, name)
        if (!out.exists()) {
            context.assets.open(name).use { input ->
                out.outputStream().use { input.copyTo(it) }
            }
        }
        return out.absolutePath
    }

    /** Solve a real capture. Returns the engine's JSON result string. */
    fun solve(
        context: Context,
        gray: ByteArray,
        width: Int,
        height: Int,
        gravity: DoubleArray,
        fovDeg: Double,
        timestampUtc: String = Instant.now().toString(),
    ): String {
        val indexPath = copyAsset(context, "index.npz")
        return module("aerogaze.mobile").callAttr(
            "solve_gray",
            gray, width, height, gravity, timestampUtc, fovDeg, indexPath
        ).toString()
    }

    /** Solve the bundled synthetic sky entirely on-device (works in airplane mode). */
    fun solveBundledDemo(context: Context): String {
        val img = copyAsset(context, "sky.png")
        val cap = copyAsset(context, "capture.json")
        val index = copyAsset(context, "index.npz")
        return module("aerogaze.mobile")
            .callAttr("solve_asset", img, cap, index).toString()
    }

    /** Bitmap -> (row-major luminance bytes, width, height) for the Python solver. */
    fun bitmapToGray(bmp: Bitmap): Triple<ByteArray, Int, Int> {
        val w = bmp.width
        val h = bmp.height
        val pixels = IntArray(w * h)
        bmp.getPixels(pixels, 0, w, 0, 0, w, h)
        val gray = ByteArray(w * h)
        for (i in pixels.indices) {
            val p = pixels[i]
            val r = (p shr 16) and 0xff
            val g = (p shr 8) and 0xff
            val b = p and 0xff
            // bit pattern is preserved; Python reads it back as unsigned uint8
            gray[i] = (0.299 * r + 0.587 * g + 0.114 * b).roundToInt().toByte()
        }
        return Triple(gray, w, h)
    }

    /** Horizontal FOV (deg) from camera characteristics; used as the solver scale prior. */
    fun horizontalFovDeg(chars: CameraCharacteristics): Double {
        val sensorW = chars.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)!!.width
        val focal = chars.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)!![0]
        return Math.toDegrees(2.0 * atan((sensorW / (2.0 * focal)).toDouble()))
    }
}
