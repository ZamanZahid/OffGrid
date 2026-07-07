import sys, time
sys.path.insert(0, r"C:\Users\Leo\BlairHacks"); sys.path.insert(0, r"C:\Users\Leo\BlairHacks\quad")
import numpy as np
from PIL import Image
from aerogaze import detect
import detect2, quadsolve

S = r"C:\Users\Leo\Downloads\aerogaze_test_images\synthetic"
R = r"C:\Users\Leo\Downloads\aerogaze_test_images\real"

print("== LONDON (fails blind) -- direct attitude search around a rough prior ==")
g = np.asarray(Image.open(S + r"\london_alt70.jpg").convert("L")); h, w = g.shape
uv, flux = detect.detect_stars(g, max_stars=60, thresh_sigma=4.0)
ra0, dec0 = quadsolve.predict_boresight(51.5074, -0.1278, "2026-01-15T22:00:00", 70, 0)
for off in (0.0, 8.0):
    t = time.time()
    r = quadsolve.solve_prior(uv, flux, w, h, ra0 + off, dec0 + off * 0.4, radius_deg=14)
    dt = time.time() - t
    if r is None: print(f"  prior off {off:3.0f} -> NO SOLVE ({dt:.1f}s)")
    else:
        ra, dec = r["center_radec_deg"]
        print(f"  prior off {off:3.0f} -> {r['n_inliers']}/{r['n_used']} inl ({r['grid_matches']} grid), "
              f"resid {r['residual_arcsec']:.0f}\", fov {r['fov_deg']:.1f}, RA={ra:.1f} Dec={dec:+.1f} ({dt:.1f}s)")

print("\n== ORION real photo (fails blind) -- prior = 'near Orion' (RA83 Dec+5) ==")
g = np.asarray(Image.open(R + r"\orion_constellation.jpg").convert("L")); h, w = g.shape
uv, flux = detect2.detect_stars2(g, max_stars=120)
t = time.time()
r = quadsolve.solve_prior(uv, flux, w, h, 83.0, 5.0, radius_deg=18,
                          fov_grid=(55, 65, 75, 85, 95))
dt = time.time() - t
if r is None: print(f"  -> NO SOLVE ({dt:.1f}s)")
else:
    ra, dec = r["center_radec_deg"]
    print(f"  -> {r['n_inliers']}/{r['n_used']} inl ({r['grid_matches']} grid), resid "
          f"{r['residual_arcsec']:.0f}\", fov {r['fov_deg']:.1f}, k1={r['k1']:+.3f}, "
          f"center RA={ra:.1f} Dec={dec:+.1f}  (Orion ~ RA83 Dec+5) ({dt:.1f}s)")
