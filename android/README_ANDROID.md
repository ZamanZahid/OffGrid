# AeroGaze on Android (Chaquopy, on-device)

The whole positioning engine is Python (numpy/scipy only). Chaquopy runs it **inside**
your Android app — no server, no network. Kotlin's job is only to (1) get a sky image,
(2) read the gravity vector + timestamp, then (3) hand them to Python and show the
result. This is designed to drop into your existing app as one screen/module.

## 1. Add Chaquopy

**Project `settings.gradle` / top-level `build.gradle`** — add the plugin (match the
latest Chaquopy version to your Android Gradle Plugin):

```gradle
plugins {
    id 'com.chaquo.python' version '15.0.1' apply false
}
```

**App `build.gradle`:**

```gradle
plugins {
    id 'com.android.application'
    id 'org.jetbrains.kotlin.android'
    id 'com.chaquo.python'
}

android {
    defaultConfig {
        ndk { abiFilters 'arm64-v8a', 'x86_64' }   // real devices + emulator
        python {
            // RETIRE THE HOUR-0 RISK: confirm these resolve for your Python/ABI.
            pip {
                install 'numpy'
                install 'scipy'
            }
        }
    }
}
```

> If `scipy` fails to resolve under your Chaquopy/Python version, the only scipy uses are
> `scipy.spatial.cKDTree` (in `solve.py`/`index_build.py`) and `scipy.ndimage` (in
> `detect.py`). Both have small numpy-only fallbacks — keep the kd-tree behind the
> `Index.neighbors_with_sep` interface and swap in a brute-force search over the
> FOV-limited candidates.

## 2. Bundle the Python + assets

```
app/src/main/python/aerogaze/        <- copy the whole aerogaze/ package here
app/src/main/assets/index.npz        <- copy data/index.npz (the catalog index)
app/src/main/assets/sky.png          <- android_assets/sky.png (indoor demo)
app/src/main/assets/capture.json     <- android_assets/capture.json (indoor demo)
```

`np.load` needs a real file path, so copy assets to `filesDir` once on first launch
(see `AeroGaze.copyAsset`).

## 3. Initialize Python (Application.onCreate)

```kotlin
if (!Python.isStarted()) Python.start(AndroidPlatform(this))
```

## 4. Use it

* **Indoor / guaranteed demo (no camera, airplane mode):** solve the bundled synthetic
  sky entirely on-device:

  ```kotlin
  val json = AeroGaze.solveBundledDemo(context)   // -> {"ok":true,"lat":...,"lon":...}
  ```

* **Real capture:** take a photo (camera intent for best night mode, or Camera2 manual
  long exposure), read gravity + timestamp, then:

  ```kotlin
  val (gray, w, h) = AeroGaze.bitmapToGray(photoBitmap)
  val gravity = skySensors.averagedGravity()       // 3 floats, see SkySensors.kt
  val json = AeroGaze.solve(context, gray, w, h, gravity, fovDeg)
  ```

`fovDeg` comes from the camera characteristics (see `AeroGaze.horizontalFovDeg`). The
solver auto-refines small scale errors, so an approximate FOV is fine.

## Result JSON

```json
{ "ok": true, "lat": 38.989, "lon": -77.029,
  "n_stars": 40, "n_inliers": 39, "residual_arcsec": 9.3 }
```

Drop `lat`/`lon` onto an offline map (osmdroid + bundled tiles) or just display them.

## What runs where

| Step | Where |
|------|-------|
| Camera capture, gravity, clock, FOV | Kotlin (`AeroGaze.kt`, `SkySensors.kt`) |
| Star detection, blind plate solve, gravity fusion, position | Python (`aerogaze/*`, via Chaquopy) |
| Catalog index + demo sky | `assets/` (built on the laptop) |
