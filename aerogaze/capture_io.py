"""Build a normalized capture from a real phone photo + an IMU log (laptop side).

This is the "manual capture" path: shoot the sky with the native camera (night/astro
mode, on a tripod), log the IMU with an app such as Sensor Logger / phyphox / Physics
Toolbox, transfer both files, and turn them into the same ``capture.json`` the solver
and the synthetic generator use.

The gravity vector is the accuracy-critical input, so we average it over a short still
window. Sensor-logger CSV layouts vary, so column detection is forgiving.
"""
from __future__ import annotations

import csv
import json

import numpy as np

# candidate column names across the common logging apps
_TIME_KEYS = ("seconds_elapsed", "time", "timestamp", "t", "elapsed")
_X_KEYS = ("x", "gravityx", "gx", "ax")
_Y_KEYS = ("y", "gravityy", "gy", "ay")
_Z_KEYS = ("z", "gravityz", "gz", "az")


def _pick(header, keys):
    low = [h.strip().lower() for h in header]
    for k in keys:
        if k in low:
            return low.index(k)
    return None


def load_gravity_csv(path):
    """Parse a gravity (or accelerometer) CSV -> (times[s], vecs[N,3])."""
    with open(path, "r", newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        ti = _pick(header, _TIME_KEYS)
        xi = _pick(header, _X_KEYS)
        yi = _pick(header, _Y_KEYS)
        zi = _pick(header, _Z_KEYS)
        if None in (xi, yi, zi):
            raise ValueError(f"could not find x/y/z columns in {header}")
        times, vecs = [], []
        for row in reader:
            try:
                vecs.append([float(row[xi]), float(row[yi]), float(row[zi])])
                times.append(float(row[ti]) if ti is not None else len(times))
            except (ValueError, IndexError):
                continue
    times = np.asarray(times, float)
    # normalize nanosecond/millisecond epoch times to seconds-from-start
    if times.size and times.max() > 1e6:
        times = (times - times.min()) / (1e9 if times.max() > 1e15 else 1e3)
    return times, np.asarray(vecs, float)


def average_gravity(times, vecs, t0=None, window_s=2.0):
    """Mean gravity over a still window centered on t0 (or the whole log if t0 None)."""
    if t0 is None or times.size == 0:
        sel = np.ones(len(vecs), bool)
    else:
        sel = np.abs(times - t0) <= window_s / 2.0
        if not sel.any():
            sel = np.ones(len(vecs), bool)
    return vecs[sel].mean(axis=0)


def build_capture(timestamp_utc, gravity_csv, fov_deg, width, height,
                  t0=None, window_s=2.0, image_name="frame.jpg", out=None):
    """Assemble (and optionally save) a capture dict from real inputs.

    ``timestamp_utc`` is the shutter time in UTC (read it from EXIF or note it at
    capture; longitude needs it accurate to ~1 s).
    """
    times, vecs = load_gravity_csv(gravity_csv)
    g = average_gravity(times, vecs, t0=t0, window_s=window_s)
    capture = {
        "timestamp_utc": timestamp_utc,
        "gravity_device": g.tolist(),
        "camera": {"fov_deg": float(fov_deg), "width": int(width), "height": int(height)},
        "image": image_name,
    }
    if out:
        with open(out, "w") as fh:
            json.dump(capture, fh, indent=2)
    return capture


def exif_timestamp_utc(image_path, utc_offset_hours=0.0):
    """Best-effort shutter time from EXIF -> ISO UTC. Prefer noting the time yourself."""
    from datetime import datetime, timedelta, timezone
    from PIL import Image

    exif = Image.open(image_path).getexif()
    raw = exif.get(36867) or exif.get(306)          # DateTimeOriginal / DateTime
    if not raw:
        raise ValueError("no EXIF timestamp; pass timestamp_utc explicitly")
    dt = datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
    dt = dt.replace(tzinfo=timezone.utc) - timedelta(hours=utc_offset_hours)
    return dt.isoformat().replace("+00:00", "Z")
