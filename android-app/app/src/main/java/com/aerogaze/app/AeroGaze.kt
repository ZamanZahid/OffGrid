package com.aerogaze.app

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import com.chaquo.python.Python
import com.chaquo.python.PyObject
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject
import java.io.File
import java.time.Instant
import kotlin.math.atan
import kotlin.math.roundToInt

/**
 * Thin Kotlin wrapper over the AeroGaze Python engine (Chaquopy).
 *
 * Kotlin supplies pixels + gravity + clock; Python returns a JSON position string:
 *   {"ok":true,"lat":..,"lon":..,"n_stars":..,"n_inliers":..,"residual_arcsec":..}
 * No network is used anywhere.
 */
object AeroGaze {

    @Synchronized
    private fun ensureStarted(context: Context) {
        if (!Python.isStarted()) Python.start(AndroidPlatform(context.applicationContext))
    }

    /** Get a Python module, starting the embedded runtime LAZILY on first use. All solve
     *  calls run on a background dispatcher, so this never blocks the main thread, and a
     *  Relay-only session never loads Python at all. */
    private fun py(context: Context, name: String): PyObject {
        ensureStarted(context)
        return Python.getInstance().getModule(name)
    }

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

    private fun readAssetText(context: Context, name: String): String =
        context.assets.open(name).bufferedReader().use { it.readText() }

    private fun decodeAsset(context: Context, name: String): Bitmap =
        context.assets.open(name).use { BitmapFactory.decodeStream(it) }

    /** Quad-index asset paths (copied to filesDir for np.load). */
    private fun quadPaths(context: Context): Array<String> = arrayOf(
        copyAsset(context, "quad_4.5.npz"),
        copyAsset(context, "quad_5.5.npz"),
        copyAsset(context, "quad_6.5.npz"))

    /**
     * Blind-solve an uploaded photo with the quad engine: it recovers the camera attitude
     * AND the field of view from the star pattern alone, so no FOV is needed. Gravity is
     * still required for position and is reconstructed from the stated camera angle
     * ([altDeg]; 90 = straight up) + [rollDeg]. Returns the engine's JSON result.
     */
    fun solveAutoHorizon(
        context: Context,
        gray: ByteArray,
        width: Int,
        height: Int,
        altDeg: Double,
        rollDeg: Double,
        timestampUtc: String,
    ): String {
        val p = quadPaths(context)
        return py(context, "aerogaze.mobile").callAttr(
            "solve_auto_horizon", gray, width, height, altDeg, rollDeg, timestampUtc,
            p[0], p[1], p[2]
        ).toString()
    }

    /**
     * Blind quad solve (auto-FOV) from a REAL device gravity vector. Used by live camera
     * capture: the IMU supplies the orientation automatically, so the user never enters a
     * camera angle and no field-of-view is needed. Same quad engine as the upload path,
     * but gravity comes from the sensors instead of a typed angle.
     */
    fun solveAuto(
        context: Context,
        gray: ByteArray,
        width: Int,
        height: Int,
        gravity: DoubleArray,
        timestampUtc: String = Instant.now().toString(),
    ): String {
        val p = quadPaths(context)
        return py(context, "aerogaze.mobile").callAttr(
            "solve_auto", gray, width, height, gravity, timestampUtc, p[0], p[1], p[2]
        ).toString()
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
        scaleRange: Double = 0.025,
        nScales: Int = 21,
    ): String {
        val indexPath = copyAsset(context, "index.npz")
        return py(context, "aerogaze.mobile").callAttr(
            "solve_gray", gray, width, height, gravity, timestampUtc, fovDeg, indexPath,
            scaleRange, nScales
        ).toString()
    }

    /**
     * Solve an uploaded photo from user-supplied capture details. With no IMU log, the
     * gravity vector is reconstructed on the Python side from the stated camera altitude
     * ([altDeg]; 90 = straight up) and [rollDeg] -- this is what makes latitude correct
     * for photos that were not shot straight up. [timestampUtc] fixes longitude. A guessed
     * FOV (no focal length in EXIF) widens the solver's scale sweep so it can still lock
     * on; a known FOV keeps the fast, narrow sweep.
     */
    fun solveUploadManual(
        context: Context,
        gray: ByteArray,
        width: Int,
        height: Int,
        altDeg: Double,
        rollDeg: Double,
        fovDeg: Double,
        fovKnown: Boolean,
        timestampUtc: String,
    ): String {
        val scaleRange = if (fovKnown) 0.025 else 0.30
        val nScales = if (fovKnown) 21 else 41
        val indexPath = copyAsset(context, "index.npz")
        return py(context, "aerogaze.mobile").callAttr(
            "solve_horizon", gray, width, height, altDeg, rollDeg, timestampUtc, fovDeg,
            indexPath, scaleRange, nScales
        ).toString()
    }

    /**
     * Solve the bundled synthetic sky entirely on-device (works in airplane mode).
     * Decodes the asset here (no Pillow needed on the phone) and reuses capture.json
     * for the gravity vector, timestamp, and FOV.
     */
    fun solveBundledDemo(context: Context): String {
        val cap = JSONObject(readAssetText(context, "capture.json"))
        val g = cap.getJSONArray("gravity_device")
        val gravity = doubleArrayOf(g.getDouble(0), g.getDouble(1), g.getDouble(2))
        val fov = cap.getJSONObject("camera").getDouble("fov_deg")
        val ts = cap.getString("timestamp_utc")
        val (gray, w, h) = bitmapToGray(decodeAsset(context, "sky.png"))
        return solve(context, gray, w, h, gravity, fov, ts)
    }

    /** Ground-truth (lat, lon) bundled with the demo, for plotting on the map. */
    fun bundledTruth(context: Context): DoubleArray? = try {
        val t = JSONObject(readAssetText(context, "capture.json")).getJSONObject("truth")
        doubleArrayOf(t.getDouble("lat"), t.getDouble("lon"))
    } catch (e: Exception) {
        null
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
            // bit pattern preserved; Python reads it back as unsigned uint8
            gray[i] = (0.299 * r + 0.587 * g + 0.114 * b).roundToInt().toByte()
        }
        return Triple(gray, w, h)
    }

    /** Horizontal FOV (deg) of the main back camera, used as the solver scale prior. */
    fun horizontalFovDeg(context: Context, default: Double = 67.0): Double = try {
        val cm = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val id = cm.cameraIdList.firstOrNull {
            cm.getCameraCharacteristics(it)
                .get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK
        } ?: cm.cameraIdList.first()
        val chars = cm.getCameraCharacteristics(id)
        val sensorW = chars.get(CameraCharacteristics.SENSOR_INFO_PHYSICAL_SIZE)!!.width
        val focal = chars.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)!![0]
        Math.toDegrees(2.0 * atan((sensorW / (2.0 * focal)).toDouble()))
    } catch (e: Exception) {
        default
    }
}
