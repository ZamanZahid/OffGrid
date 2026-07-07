import sys
sys.path.insert(0, r"C:\Users\Leo\BlairHacks"); sys.path.insert(0, r"C:\Users\Leo\BlairHacks\quad")
import numpy as np
from PIL import Image
from aerogaze import detect
import detect2, quadsolve

S = r"C:\Users\Leo\Downloads\aerogaze_test_images\synthetic"
R = r"C:\Users\Leo\Downloads\aerogaze_test_images\real"

print("== LONDON (fails BLIND) -- warm-start with a rough location prior ==")
g = np.asarray(Image.open(S + r"\london_alt70.jpg").convert("L")); h, w = g.shape
uv, flux = detect.detect_stars(g, max_stars=60, thresh_sigma=4.0)
# true boresight for London shot, then a ROUGH prior offset ~4 deg (sensor+location error)
true_ra, true_dec = quadsolve.predict_boresight(51.5074, -0.1278, "2026-01-15T22:00:00", 70, 0)
for off in (0.0, 6.0, 15.0):
    pr, pd = true_ra + off, true_dec + off * 0.5
    r = quadsolve.solve_local(uv, flux, w, h, pr, pd, radius_deg=22.0)
    if r is None:
        print(f"  prior off {off:4.0f} deg -> NO SOLVE")
    else:
        ra, dec = r["center_radec_deg"]
        print(f"  prior off {off:4.0f} deg -> {r['n_inliers']}/{r['n_used']} inl, resid "
              f"{r['residual_arcsec']:.0f}\", fov {r['fov_deg']:.1f}, center RA={ra:.1f} Dec={dec:+.1f}")

print("\n== ORION real photo (fails BLIND) -- prior = sensors say 'near Orion' (RA83 Dec+5) ==")
g = np.asarray(Image.open(R + r"\orion_constellation.jpg").convert("L")); h, w = g.shape
uv, flux = detect2.detect_stars2(g, max_stars=120)
for rad in (18.0, 25.0, 35.0):
    r = quadsolve.solve_local(uv, flux, w, h, 83.0, 5.0, radius_deg=rad)
    if r is None:
        print(f"  radius {rad:4.0f} deg -> NO SOLVE")
    else:
        ra, dec = r["center_radec_deg"]
        print(f"  radius {rad:4.0f} deg -> {r['n_inliers']}/{r['n_used']} inl, resid "
              f"{r['residual_arcsec']:.0f}\", fov {r['fov_deg']:.1f}, k1={r['k1']:+.3f}, "
              f"center RA={ra:.1f} Dec={dec:+.1f}")
