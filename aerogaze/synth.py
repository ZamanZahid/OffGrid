"""Synthetic night-sky generator (laptop only).

Renders a star image for a chosen (lat, lon, utc) and camera attitude, plus a
self-consistent ``capture`` dict (gravity vector, timestamp, intrinsics) and the
ground-truth. This is the backbone demo + the roundtrip test fixture: it works
indoors at noon and proves the solver recovers the position deterministically.

The camera attitude is given in the local horizon frame as (alt, az, roll):
alt/az of the boresight (alt=90 = straight up at the zenith; az from north toward
east) and a roll about the boresight.
"""
from __future__ import annotations

import numpy as np

from . import astro_lite, geometry
from .catalog import load_hyg

# device frame == camera frame for synthetic captures (extrinsic = identity)


def _local_enu_icrs(zenith_icrs, jd):
    """East/North/Up unit vectors (in ICRS) of the local horizon frame."""
    up = geometry.normalize(zenith_icrs)
    pole = astro_lite.precession_matrix(jd).T @ np.array([0.0, 0.0, 1.0])  # NCP of date
    north = geometry.normalize(pole - np.dot(pole, up) * up)
    east = np.cross(north, up)
    return east, north, up


def attitude_for(lat, lon, utc, alt=90.0, az=0.0, roll=0.0):
    """Return (R_cam2sky, zenith_icrs, gravity_device) for a horizon-frame attitude."""
    jd = astro_lite.julian_date(utc)
    zenith_icrs = astro_lite.latlon_to_zenith_icrs(lat, lon, utc)
    east, north, up = _local_enu_icrs(zenith_icrs, jd)

    a, z = np.radians(alt), np.radians(az)
    boresight = (np.cos(a) * np.sin(z) * east
                 + np.cos(a) * np.cos(z) * north
                 + np.sin(a) * up)
    ra, dec = geometry.vec_to_radec(boresight)
    R = geometry.rotation_from_boresight(ra, dec, np.radians(roll))

    # gravity points opposite the zenith, expressed in the camera/device frame
    gravity_device = -(R.T @ zenith_icrs)
    return R, zenith_icrs, geometry.normalize(gravity_device)


def render(cat, R_cam2sky, fov_deg=60.0, width=1024, height=768,
           psf_sigma=1.4, flux_scale=5000.0, bg=6.0, noise=2.0,
           n_spurious=3, n_missing=2, seed=0):
    """Render a grayscale (H, W) uint8 star image for the given attitude.

    Returns (image, truth_uv, truth_mask) where truth_uv are the projected catalog
    pixel positions and truth_mask marks which catalog stars are in-frame.
    """
    rng = np.random.default_rng(seed)
    focal = geometry.focal_px_from_fov(fov_deg, width)
    uv, vis = geometry.project(cat.vec, R_cam2sky, focal, width, height)

    img = bg + rng.normal(0.0, noise, size=(height, width))
    idx = np.where(vis)[0]
    if n_missing and len(idx) > n_missing:                    # drop a few real stars
        drop = set(rng.choice(idx, size=n_missing, replace=False).tolist())
        idx = np.array([i for i in idx if i not in drop])

    yy, xx = np.mgrid[0:height, 0:width]
    for i in idx:
        u, v = uv[i]
        peak = min(255.0, flux_scale * 10 ** (-0.4 * cat.mag[i]))
        lo_x, hi_x = max(0, int(u - 6)), min(width, int(u + 7))
        lo_y, hi_y = max(0, int(v - 6)), min(height, int(v + 7))
        if hi_x <= lo_x or hi_y <= lo_y:
            continue
        sx = xx[lo_y:hi_y, lo_x:hi_x] - u
        sy = yy[lo_y:hi_y, lo_x:hi_x] - v
        img[lo_y:hi_y, lo_x:hi_x] += peak * np.exp(-(sx * sx + sy * sy) / (2 * psf_sigma ** 2))

    for _ in range(n_spurious):                              # hot pixels / artifacts
        u, v = rng.uniform(0, width), rng.uniform(0, height)
        peak = rng.uniform(20, 120)
        lo_x, hi_x = max(0, int(u - 4)), min(width, int(u + 5))
        lo_y, hi_y = max(0, int(v - 4)), min(height, int(v + 5))
        sx = xx[lo_y:hi_y, lo_x:hi_x] - u
        sy = yy[lo_y:hi_y, lo_x:hi_x] - v
        img[lo_y:hi_y, lo_x:hi_x] += peak * np.exp(-(sx * sx + sy * sy) / (2 * psf_sigma ** 2))

    return np.clip(img, 0, 255).astype(np.uint8), uv, vis


def make_capture(lat, lon, utc, alt=90.0, az=0.0, roll=0.0,
                 fov_deg=60.0, width=1024, height=768, mag_limit=6.5,
                 cat=None, **render_kw):
    """Produce (image, capture_dict, truth_dict) for a synthetic observation."""
    if cat is None:
        cat = load_hyg(mag_limit=mag_limit)
    R, zenith_icrs, gravity = attitude_for(lat, lon, utc, alt, az, roll)
    img, uv, vis = render(cat, R, fov_deg=fov_deg, width=width, height=height, **render_kw)
    capture = {
        "timestamp_utc": utc,
        "gravity_device": gravity.tolist(),
        "camera": {"fov_deg": fov_deg, "width": width, "height": height},
    }
    truth = {
        "lat": lat, "lon": lon, "alt": alt, "az": az, "roll": roll,
        "R_cam2sky": R, "zenith_icrs": zenith_icrs,
        "n_visible": int(vis.sum()),
    }
    return img, capture, truth
