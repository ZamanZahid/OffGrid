"""On-device entry point called from Kotlin via Chaquopy.

Keep this surface tiny and JSON-friendly: Kotlin hands over the decoded grayscale
image plus the gravity vector, timestamp, and camera FOV; we return a JSON string with
the computed position. The heavy index is loaded once and cached across calls.

Everything here is numpy/scipy only -- no astropy, no Pillow required on the phone
(Kotlin decodes the bitmap; for the bundled synthetic demo we optionally use Pillow).
"""
from __future__ import annotations

import json
import os

import numpy as np

from . import orient, pipeline, solve

_INDEX = None
_INDEX_PATH = None


def load_index(index_path):
    """Load (and cache) the catalog index shipped as an app asset."""
    global _INDEX, _INDEX_PATH
    if _INDEX is None or index_path != _INDEX_PATH:
        _INDEX = solve.load_index(index_path)
        _INDEX_PATH = index_path
    return _INDEX


def solve_gray(gray, width, height, gravity, timestamp_utc, fov_deg, index_path,
               scale_range=0.025, n_scales=21):
    """Solve from a flat row-major grayscale buffer.

    Parameters
    ----------
    gray : sequence/bytes/ndarray of length width*height, uint8 luminance.
    gravity : 3 floats, device-frame accelerometer "down" vector (any scale).
    timestamp_utc : ISO-8601 string from the device clock.
    fov_deg : horizontal field of view of the camera.
    index_path : filesystem path to index.npz (an app asset).
    scale_range, n_scales : FOV-sweep width + samples for the blind solver. Widen these
        (e.g. 0.30) when ``fov_deg`` is only a guess -- e.g. an uploaded photo with no
        focal length in EXIF -- so the solver can still find the true scale.

    Returns a JSON string: {ok, lat, lon, n_stars, n_inliers, residual_arcsec}.
    """
    img = np.frombuffer(bytes(gray), dtype=np.uint8).reshape(int(height), int(width))
    capture = {
        "timestamp_utc": str(timestamp_utc),
        "gravity_device": [float(g) for g in gravity],
        "camera": {"fov_deg": float(fov_deg), "width": int(width), "height": int(height)},
    }
    return _solve_capture(capture, img, index_path, float(scale_range), int(n_scales))


def solve_horizon(gray, width, height, alt_deg, roll_deg, timestamp_utc, fov_deg,
                  index_path, scale_range=0.30, n_scales=41):
    """Solve an uploaded photo from a user-stated camera angle instead of an IMU log.

    ``alt_deg`` is the camera's elevation above the horizon (90 = straight up at the
    zenith); ``roll_deg`` is the roll about the view axis (0 = phone upright). The
    gravity vector is reconstructed from these (see :func:`orient.gravity_from_horizon`)
    -- this is what fixes latitude for photos that were not shot straight up. Other
    arguments match :func:`solve_gray`.
    """
    img = np.frombuffer(bytes(gray), dtype=np.uint8).reshape(int(height), int(width))
    gravity = orient.gravity_from_horizon(float(alt_deg), float(roll_deg))
    capture = {
        "timestamp_utc": str(timestamp_utc),
        "gravity_device": [float(g) for g in gravity],
        "camera": {"fov_deg": float(fov_deg), "width": int(width), "height": int(height)},
    }
    return _solve_capture(capture, img, index_path, float(scale_range), int(n_scales))


_QUAD_LAYERS = None
_QUAD_KEY = None


def _quad_layers(paths):
    """Load (and cache) the quad index layers shipped as app assets."""
    global _QUAD_LAYERS, _QUAD_KEY
    key = tuple(str(p) for p in paths)
    if _QUAD_LAYERS is None or key != _QUAD_KEY:
        from . import quadmobile
        _QUAD_LAYERS = quadmobile.load_layers(list(key), cell=0.013)
        _QUAD_KEY = key
    return _QUAD_LAYERS


def _solve_auto(gray, width, height, gravity, timestamp_utc, paths):
    """Quad-engine blind solve: detect stars, recover attitude + FOV with no hints, then
    fuse with gravity to a position. Returns the same JSON shape as solve_gray."""
    from . import detect, quadmobile
    img = np.frombuffer(bytes(gray), dtype=np.uint8).reshape(int(height), int(width))
    uv, flux = detect.detect_stars(img, max_stars=70, thresh_sigma=4.0)
    res = quadmobile.solve(uv, flux, int(width), int(height), _quad_layers(paths))
    if res is None or res["n_inliers"] < max(12, 0.45 * res["n_stars"]):
        return json.dumps({"ok": False,
                           "error": "sky not confidently identified -- need a clearer, "
                                    "wider shot with more naked-eye stars"})
    capture = {"timestamp_utc": str(timestamp_utc),
               "gravity_device": [float(g) for g in gravity]}
    fix = pipeline.solve_from_attitude(capture, res["R_cam2sky"])
    return json.dumps({
        "ok": True, "lat": round(fix.lat, 5), "lon": round(fix.lon, 5),
        "n_stars": res["n_stars"], "n_inliers": res["n_inliers"],
        "residual_arcsec": round(res["residual_arcsec"], 1),
        "fov_deg": round(res["fov_deg"], 1),
    })


def solve_auto(gray, width, height, gravity, timestamp_utc, path0, path1, path2):
    """FOV-free blind solve from an explicit gravity vector (e.g. the bundled demo)."""
    return _solve_auto(gray, width, height, [float(g) for g in gravity],
                       timestamp_utc, (path0, path1, path2))


def solve_auto_horizon(gray, width, height, alt_deg, roll_deg, timestamp_utc,
                       path0, path1, path2):
    """FOV-free blind solve for an uploaded photo: gravity from the stated camera angle."""
    gravity = orient.gravity_from_horizon(float(alt_deg), float(roll_deg))
    return _solve_auto(gray, width, height, gravity, timestamp_utc, (path0, path1, path2))


def solve_asset(image_path, capture_json_path, index_path):
    """Solve a bundled synthetic asset (PNG + capture.json) -- the indoor demo path."""
    from PIL import Image
    img = np.asarray(Image.open(image_path).convert("L"))
    with open(capture_json_path) as fh:
        capture = json.load(fh)
    h, w = img.shape
    capture.setdefault("camera", {}).update({"width": int(w), "height": int(h)})
    return _solve_capture(capture, img, index_path)


def _solve_capture(capture, img, index_path, scale_range=0.025, n_scales=21):
    index = load_index(index_path)
    try:
        fix = pipeline.solve(capture, img, index,
                             scale_range=scale_range, n_scales=n_scales)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps({
        "ok": True,
        "lat": round(fix.lat, 5),
        "lon": round(fix.lon, 5),
        "n_stars": fix.n_stars,
        "n_inliers": fix.n_inliers,
        "residual_arcsec": round(fix.residual_arcsec, 1),
    })


if __name__ == "__main__":
    # simulate the on-device call using the bundled demo asset
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(solve_asset(
        os.path.join(root, "android_assets", "sky.png"),
        os.path.join(root, "android_assets", "capture.json"),
        os.path.join(root, "data", "index.npz"),
    ))
