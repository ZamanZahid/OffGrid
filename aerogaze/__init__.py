"""AeroGaze AI - offline celestial positioning engine.

Computes global coordinates (latitude/longitude) from a night-sky photo plus the
device's gravity vector and clock, with no network. Pure numpy/scipy so the solver
runs identically on a laptop and on-device (Chaquopy) inside an Android app.
"""



__all__ = [
    "geometry",
    "catalog",
    "astro_lite",
    "synth",
    "detect",
    "orient",
    "pipeline",
]
