# AeroGaze — Android app (Chaquopy, on-device)

A complete standalone app that runs the AeroGaze positioning engine **on the phone** via
Chaquopy (Python-in-Android). No network, no GPS. Self-contained so it can be merged into
another app later (everything lives under `com.aerogaze.app` + `src/main/python/aerogaze`
+ four assets).

## Build & run

1. **Open `android-app/` in Android Studio.** Use its **embedded JDK 17** (Settings →
   Build Tools → Gradle → Gradle JDK). The system JDK here is 23, which AGP/Gradle 8.7
   rejects — Android Studio's bundled 17 avoids that. (The Gradle wrapper is included and
   pinned to Gradle 8.7; for a CLI build point `JAVA_HOME` at a JDK 17 and run
   `gradlew assembleDebug`.)
2. **Install Python 3.12** on the build machine (Chaquopy runs `pip` through a matching
   `buildPython`; the system Python is 3.13). If Studio can't find it, add to
   `app/build.gradle` → `defaultConfig.python`:
   `buildPython "C:\\Path\\To\\Python312\\python.exe"`.
3. **Gradle sync** (downloads Chaquopy + the numpy wheel from `chaquo.com/maven`).
4. **Run** on an emulator (`x86_64`) or a device (`arm64-v8a`).

> Versions are pinned in `build.gradle` (AGP 8.5.2, Gradle 8.7, Kotlin 1.9.24,
> Chaquopy 15.0.1, compile/target SDK 34, minSdk 26). If they conflict on your setup,
> bump AGP ↔ Gradle ↔ Chaquopy together — they must be mutually compatible.

## What it does

- **Demo (offline):** solves the bundled synthetic sky `assets/sky.png` entirely
  on-device — works in **airplane mode**. Expect ≈ `38.99, -77.03` (Silver Spring) with a
  pin on the map and the recovered-vs-truth error in km.
- **Capture & solve:** opens the native camera (use night/astro mode on a tripod), reads
  the fused gravity vector, and solves the real sky on-device.

## How it's wired

| Piece | File |
|-------|------|
| Start Python once | `AeroGazeApp.kt` (`Python.start`) |
| Call the engine, decode bitmaps, FOV | `AeroGaze.kt` |
| Gravity / attitude sensors | `SkySensors.kt` |
| Camera intent + downsample | `CameraCapture.kt` |
| Offline map + pin | `WorldMapView.kt` |
| UI / flow | `MainActivity.kt`, `res/layout/activity_main.xml` |
| Engine (numpy-only) | `src/main/python/aerogaze/*` |
| Catalog index + demo sky + map | `src/main/assets/{index.npz,sky.png,capture.json,world.png}` |

The engine returns JSON: `{ok, lat, lon, n_stars, n_inliers, residual_arcsec}`.

## Notes / known limitations (v1)

- **Gravity timing:** during the camera intent the activity is backgrounded, so gravity is
  sampled for ~2 s *after* you return — hold the same orientation you shot in. A
  foreground-service sampler is the proper fix later.
- **Image orientation:** the captured JPEG is used as-is. If a device applies EXIF
  rotation, the camera↔device frame can be off by 90°; handle display/EXIF rotation before
  the real-photo path is production-ready. The synthetic demo is unaffected.
- **FOV:** taken from the main back-camera characteristics (falls back to 67°); the solver
  auto-refines small scale errors.
- **`world.png`** is a graticule placeholder. Drop in a public-domain equirectangular world
  image (e.g. Natural Earth 1:110m) at `assets/world.png` for a real-looking map.

## Regenerating the assets

From the repo root (laptop): `python -m aerogaze.index_build` and `python scripts/demo.py`,
then copy `data/index.npz` and `android_assets/{sky.png,capture.json}` into
`app/src/main/assets/`.
