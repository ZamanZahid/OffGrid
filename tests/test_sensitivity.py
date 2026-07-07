"""Error-model sanity: confirm position error scales as the physics predicts.

These are the numbers behind the pitch:
* a tilt error in the gravity vector maps ~1 deg -> ~111 km (1 deg of arc on Earth);
* a clock error maps ~1 s -> Earth rotates 15 arcsec -> ~0.46*cos(lat) km of longitude.
"""
import numpy as np

from aerogaze import geometry, pipeline, synth
from aerogaze.catalog import load_hyg

CAT = load_hyg(mag_limit=6.5)
LAT, LON, UTC = 38.99, -77.03, "2026-06-26T04:30:00"


def _err_km(lat1, lon1, lat2, lon2):
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def _rotate_about(vec, axis, angle_rad):
    axis = geometry.normalize(axis)
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return vec * c + np.cross(axis, vec) * s + axis * np.dot(axis, vec) * (1 - c)


def test_tilt_one_degree_is_about_111km():
    _, cap, truth = synth.make_capture(LAT, LON, UTC, cat=CAT)
    g = np.array(cap["gravity_device"])
    perp = geometry.normalize(np.cross(g, [1.0, 0.0, 0.0]))
    cap2 = dict(cap, gravity_device=_rotate_about(g, perp, np.radians(1.0)).tolist())
    fix = pipeline.solve_from_attitude(cap2, truth["R_cam2sky"])
    err = _err_km(LAT, LON, fix.lat, fix.lon)
    assert 90.0 < err < 130.0, f"1 deg tilt -> {err:.1f} km"


def test_one_second_clock_error_is_sub_km():
    _, cap, truth = synth.make_capture(LAT, LON, UTC, cat=CAT)
    cap2 = dict(cap, timestamp_utc="2026-06-26T04:30:01")  # +1 s
    fix = pipeline.solve_from_attitude(cap2, truth["R_cam2sky"])
    err = _err_km(LAT, LON, fix.lat, fix.lon)
    assert 0.1 < err < 0.8, f"1 s clock error -> {err:.3f} km"
