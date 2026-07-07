"""End-to-end pipeline: a capture (+ image) -> (latitude, longitude).

Two entry points:
* :func:`solve_from_attitude` -- position given a known camera attitude (used by the
  synthetic roundtrip test and any case where orientation is supplied directly).
* :func:`solve` -- the full on-device path: detect stars, blind plate-solve against
  the catalog index, fuse with gravity, compute position.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import astro_lite, detect, orient


@dataclass
class Fix:
    lat: float
    lon: float
    zenith_icrs: np.ndarray
    n_stars: int = 0
    n_inliers: int = 0
    residual_arcsec: float = float("nan")


def solve_from_attitude(capture, R_cam2sky):
    """Position from a known camera attitude + the capture's gravity & timestamp."""
    zenith = orient.zenith_from_attitude(R_cam2sky, capture["gravity_device"])
    lat, lon = astro_lite.zenith_to_latlon(zenith, capture["timestamp_utc"])
    return Fix(lat=lat, lon=lon, zenith_icrs=zenith)


def solve(capture, image, index, scale_range=0.025, n_scales=21, **detect_kw):
    """Full blind solve from a raw image + capture metadata.

    ``index`` is a prebuilt catalog hash index (see :mod:`aerogaze.index_build`).
    ``scale_range``/``n_scales`` set the blind solver's FOV-uncertainty sweep (widen
    them when ``capture["camera"]["fov_deg"]`` is only a guess). Raises ValueError if
    the sky cannot be identified.
    """
    from . import solve as _solve  # local import: heavy, optional on some paths

    uv, flux = detect.detect_stars(image, **detect_kw)
    cam = capture["camera"]
    result = _solve.blind_solve_multiscale(
        uv, cam["fov_deg"], cam["width"], cam["height"], index,
        scale_range=scale_range, n_scales=n_scales)
    if result is None:
        raise ValueError("plate solve failed: sky not identified")

    # Confidence gate. A genuine identification explains most of the detected stars
    # (high inlier fraction) with a small angular residual. A *false* lock -- common on
    # processed/stretched photos, unknown lenses, or too few real stars -- explains only
    # a minority and/or fits badly. Reject those so we never report a confidently wrong
    # position. Thresholds: true solves here run >=0.9 fraction at <25"; false locks run
    # ~0.2 fraction or hundreds of arcsec, so 0.45 / 300" separates them with wide margin.
    n_stars = len(uv)
    if n_stars == 0 or result.n_inliers < 0.45 * n_stars \
            or result.residual_arcsec > 300.0:
        raise ValueError("sky not confidently identified -- need a clearer, wider "
                         "shot with more naked-eye stars (and a correct angle/FOV)")

    fix = solve_from_attitude(capture, result.R_cam2sky)
    fix.n_stars = len(uv)
    fix.n_inliers = result.n_inliers
    fix.residual_arcsec = result.residual_arcsec
    return fix
