"""Manual-path glue test: synth gravity -> sensor-logger-style CSV -> capture -> solve.

Proves the real-photo pipeline (image + IMU log -> capture.json -> position) works,
without needing an actual phone, by writing the synthetic gravity into a CSV exactly
like a logging app would and rebuilding the capture from it.
"""
import numpy as np

from aerogaze import capture_io, detect, pipeline, solve, synth
from aerogaze.catalog import load_hyg

CAT = load_hyg(mag_limit=6.5)
INDEX = solve.load_index()



def _err_km(a, b, c, d):
    dlat, dlon = np.radians(c - a), np.radians(d - b)
    h = np.sin(dlat / 2) ** 2 + np.cos(np.radians(a)) * np.cos(np.radians(c)) * np.sin(dlon / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(h))


def test_manual_capture_roundtrip(tmp_path):
    lat, lon, utc = 38.99, -77.03, "2026-06-26T04:30:00"
    img, cap, _ = synth.make_capture(lat, lon, utc, alt=83, az=35, roll=18,
                                     fov_deg=60, width=1024, height=768, cat=CAT, seed=11)

    # write the gravity as a Sensor-Logger-style CSV (jittered, still window)
    g = np.array(cap["gravity_device"])
    csv_path = tmp_path / "Gravity.csv"
    rng = np.random.default_rng(0)
    with open(csv_path, "w") as fh:
        fh.write("seconds_elapsed,x,y,z\n")
        for k in range(40):
            j = g + rng.normal(0, 0.01, 3)
            fh.write(f"{k * 0.05:.3f},{j[0]:.5f},{j[1]:.5f},{j[2]:.5f}\n")

    rebuilt = capture_io.build_capture(utc, str(csv_path), fov_deg=60,
                                       width=1024, height=768, window_s=2.0)

    fix = pipeline.solve(rebuilt, img, INDEX)
    assert _err_km(lat, lon, fix.lat, fix.lon) < 10.0
