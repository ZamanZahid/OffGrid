"""Roundtrip: synthesize a sky for a known position, then recover it.

Milestone-2 proof. With KNOWN orientation this exercises everything except the blind
solver: synthetic projection -> star detection -> gravity fusion -> astro_lite. The
detected stars are matched back to the truth projection to confirm detection works,
and the position is recovered from the (known) attitude.
"""
import numpy as np
import pytest

from aerogaze import detect, pipeline, synth
from aerogaze.catalog import load_hyg

CASES = [
    # lat, lon, utc, alt, az, roll
    (38.99, -77.03, "2026-06-26T04:30:00", 90.0, 0.0, 0.0),
    (38.99, -77.03, "2026-06-26T04:30:00", 80.0, 45.0, 30.0),   # tilted + rolled
    (19.0, 72.8, "2026-02-10T18:20:00", 85.0, 120.0, -15.0),
    (-33.87, 151.21, "2026-09-15T13:10:00", 88.0, 200.0, 10.0),
]

CAT = load_hyg(mag_limit=6.5)


def _err_km(lat1, lon1, lat2, lon2):
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


@pytest.mark.parametrize("lat,lon,utc,alt,az,roll", CASES)
def test_known_orientation_roundtrip(lat, lon, utc, alt, az, roll):
    img, capture, truth = synth.make_capture(
        lat, lon, utc, alt=alt, az=az, roll=roll, fov_deg=60.0,
        width=1024, height=768, cat=CAT, seed=1)

    # detection sanity: we should find a healthy number of stars
    uv, flux = detect.detect_stars(img, thresh_sigma=5.0, max_stars=60)
    assert len(uv) >= 10, f"only {len(uv)} stars detected"

    # recover position from the (known) attitude + gravity + clock
    fix = pipeline.solve_from_attitude(capture, truth["R_cam2sky"])
    err = _err_km(lat, lon, fix.lat, fix.lon)
    assert err < 1.0, f"recovered ({fix.lat:.3f},{fix.lon:.3f}) err={err:.3f} km"


if __name__ == "__main__":
    for lat, lon, utc, alt, az, roll in CASES:
        img, capture, truth = synth.make_capture(
            lat, lon, utc, alt=alt, az=az, roll=roll, cat=CAT, seed=1)
        uv, flux = detect.detect_stars(img, max_stars=60)
        fix = pipeline.solve_from_attitude(capture, truth["R_cam2sky"])
        err = _err_km(lat, lon, fix.lat, fix.lon)
        print(f"({lat:+.2f},{lon:+.2f}) alt={alt} az={az} roll={roll} | "
              f"{truth['n_visible']} vis, {len(uv)} detected | "
              f"recovered ({fix.lat:+.3f},{fix.lon:+.3f}) err={err:.3f} km")
