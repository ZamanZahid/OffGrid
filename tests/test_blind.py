"""Blind solver tests: recover position from a raw synthetic image with no prior.

Covers clean skies, noisier images, varied fields of view, and a small field-of-view
(scale) mismatch to model real-camera intrinsic uncertainty.
"""
import numpy as np
import pytest

from aerogaze import detect, pipeline, solve, synth
from aerogaze.catalog import load_hyg

CAT = load_hyg(mag_limit=6.5)
INDEX = solve.load_index()



def _err_km(lat1, lon1, lat2, lon2):
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


CASES = [
    (38.99, -77.03, "2026-06-26T04:30:00", 90, 0, 0, 60.0),
    (38.99, -77.03, "2026-06-26T04:30:00", 80, 45, 30, 60.0),
    (19.0, 72.8, "2026-02-10T18:20:00", 85, 120, -15, 50.0),
    (-33.87, 151.21, "2026-09-15T13:10:00", 88, 200, 10, 70.0),
    (51.5, -0.13, "2026-11-05T22:00:00", 75, 300, 5, 65.0),
]


@pytest.mark.parametrize("lat,lon,utc,alt,az,roll,fov", CASES)
def test_blind_clean(lat, lon, utc, alt, az, roll, fov):
    img, cap, _ = synth.make_capture(lat, lon, utc, alt=alt, az=az, roll=roll,
                                     fov_deg=fov, width=1024, height=768, cat=CAT, seed=1)
    uv, _ = detect.detect_stars(img, thresh_sigma=5, max_stars=40)
    res = solve.blind_solve(uv, fov, 1024, 768, INDEX)
    assert res is not None, "blind solve failed"
    fix = pipeline.solve_from_attitude(cap, res.R_cam2sky)
    assert _err_km(lat, lon, fix.lat, fix.lon) < 5.0


def test_blind_noisy():
    """Lower SNR + more artifacts; should still solve."""
    lat, lon, utc = 38.99, -77.03, "2026-06-26T04:30:00"
    img, cap, _ = synth.make_capture(lat, lon, utc, alt=85, az=20, roll=12,
                                     fov_deg=60, width=1024, height=768, cat=CAT,
                                     noise=4.0, n_spurious=8, n_missing=4, seed=7)
    uv, _ = detect.detect_stars(img, thresh_sigma=5, max_stars=40)
    res = solve.blind_solve(uv, 60, 1024, 768, INDEX)
    assert res is not None and res.n_inliers >= 10
    fix = pipeline.solve_from_attitude(cap, res.R_cam2sky)
    assert _err_km(lat, lon, fix.lat, fix.lon) < 10.0


def test_blind_fov_mismatch():
    """Solver told the FOV is 2% off (camera intrinsic uncertainty)."""
    lat, lon, utc = 19.0, 72.8, "2026-02-10T18:20:00"
    img, cap, _ = synth.make_capture(lat, lon, utc, alt=88, az=120, roll=-15,
                                     fov_deg=60.0, width=1024, height=768, cat=CAT, seed=3)
    uv, _ = detect.detect_stars(img, thresh_sigma=5, max_stars=40)
    res = solve.blind_solve_multiscale(uv, 61.2, 1024, 768, INDEX)  # 2% wrong FOV
    assert res is not None
    fix = pipeline.solve_from_attitude(cap, res.R_cam2sky)
    assert _err_km(lat, lon, fix.lat, fix.lon) < 25.0
