package com.aerogaze.app

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import kotlin.math.atan

/**
 * Lets the user pick an existing night-sky photo from the gallery and solve it.
 *
 * An uploaded image carries no live gravity reading or reliable clock, so the user states
 * the capture time and camera angle (see MainActivity's dialog). EXIF only *pre-fills*
 * those: the capture time (GPS time -> DateTimeOriginal + offset/zone) and the field of
 * view (from the 35 mm-equivalent focal length). We deliberately use ACTION_OPEN_DOCUMENT
 * so that EXIF survives -- the system photo picker redacts it.
 */
object ImagePicker {
    const val REQUEST_CODE = 1002

    /**
     * "Pick an image" intent. We use ACTION_OPEN_DOCUMENT (Storage Access Framework)
     * rather than ACTION_GET_CONTENT on purpose: the system photo picker that
     * ACTION_GET_CONTENT now routes to *redacts EXIF* (time, focal length) for privacy,
     * and we need those to compute longitude + scale. SAF returns the raw file intact.
     */
    fun intent(): Intent =
        Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            type = "image/*"
            addCategory(Intent.CATEGORY_OPENABLE)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }

    /** Decode the picked image, downsampled so on-device detection stays light. */
    fun decodeDownsampled(context: Context, uri: Uri, maxWidth: Int = 1600): Bitmap {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        }
        var sample = 1
        while (bounds.outWidth / sample > maxWidth) sample *= 2
        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        return context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, opts)
        } ?: error("Could not open the selected image")
    }

    /** What we could glean from EXIF; either field may be null when the photo lacks it. */
    data class Meta(val timestampUtc: String?, val fovDeg: Double?)

    private val EXIF_DATETIME = DateTimeFormatter.ofPattern("yyyy:MM:dd HH:mm:ss")

    /** Read capture time + FOV from the photo's EXIF metadata. */
    fun readMeta(context: Context, uri: Uri): Meta {
        val exif = context.contentResolver.openInputStream(uri)?.use { ExifInterface(it) }
            ?: return Meta(null, null)
        return Meta(exifTimestampUtc(exif), exifFovDeg(exif))
    }

    /**
     * Capture time as an ISO-8601 UTC string. Prefer the GPS clock (already UTC), then
     * DateTimeOriginal with its EXIF UTC offset; if no offset is recorded we fall back to
     * the device's current time zone, which is the best guess available.
     */
    private fun exifTimestampUtc(exif: ExifInterface): String? {
        val gps = exif.gpsDateTime                       // ms since epoch (UTC); null/-1 if absent
        if (gps != null && gps > 0L) return Instant.ofEpochMilli(gps).toString()

        val raw = exif.getAttribute(ExifInterface.TAG_DATETIME_ORIGINAL)
            ?: exif.getAttribute(ExifInterface.TAG_DATETIME) ?: return null
        val local = try {
            LocalDateTime.parse(raw.trim(), EXIF_DATETIME)
        } catch (e: Exception) {
            return null
        }
        val offset = exif.getAttribute(ExifInterface.TAG_OFFSET_TIME_ORIGINAL)
            ?: exif.getAttribute(ExifInterface.TAG_OFFSET_TIME)
        val instant = if (offset != null) {
            try {
                OffsetDateTime.of(local, ZoneOffset.of(offset.trim())).toInstant()
            } catch (e: Exception) {
                local.atZone(ZoneId.systemDefault()).toInstant()
            }
        } else {
            local.atZone(ZoneId.systemDefault()).toInstant()
        }
        return instant.toString()
    }

    /** Horizontal FOV from the 35 mm-equivalent focal length: 2*atan(36 / (2*f)). */
    private fun exifFovDeg(exif: ExifInterface): Double? {
        val f35 = exif.getAttributeInt(ExifInterface.TAG_FOCAL_LENGTH_IN_35MM_FILM, 0)
        return if (f35 > 0) Math.toDegrees(2.0 * atan(36.0 / (2.0 * f35))) else null
    }
}
