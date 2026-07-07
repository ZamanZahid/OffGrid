package com.aerogaze.app

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.MediaStore
import androidx.core.content.FileProvider
import java.io.File

/** Launches the native camera (best night mode) and reads the photo back. */
object CameraCapture {
    const val REQUEST_CODE = 1001

    fun newPhotoFile(context: Context): File {
        val dir = File(context.getExternalFilesDir(null), "captures").apply { mkdirs() }
        return File(dir, "sky_${System.currentTimeMillis()}.jpg")
    }

    fun intentFor(context: Context, file: File): Intent {
        val uri: Uri = FileProvider.getUriForFile(
            context, "${context.packageName}.fileprovider", file)
        return Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
            putExtra(MediaStore.EXTRA_OUTPUT, uri)
            addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        }
    }

    /** Decode the captured JPEG, downsampled so on-device detection stays light. */
    fun decodeDownsampled(path: String, maxWidth: Int = 1600): Bitmap {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(path, bounds)
        var sample = 1
        while (bounds.outWidth / sample > maxWidth) sample *= 2
        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        return BitmapFactory.decodeFile(path, opts)
    }
}
