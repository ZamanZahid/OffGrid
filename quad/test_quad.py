import sys, time
sys.path.insert(0, r"C:\Users\Leo\BlairHacks")
sys.path.insert(0, r"C:\Users\Leo\BlairHacks\quad")
import numpy as np
from PIL import Image
from aerogaze import detect
import quadsolve

t = time.time()
layers = quadsolve.build_layers(mags=(4.5, 5.5, 6.5), verify_mag=7.5)
print(f"layers ready in {time.time()-t:.1f}s\n")

def run(path, max_stars, label, truth=None):
    g = np.asarray(Image.open(path).convert("L"))
    h, w = g.shape
    uv, flux = detect.detect_stars(g, max_stars=max_stars, thresh_sigma=4.0)
    t0 = time.time()
    r = quadsolve.solve(uv, flux, w, h, layers)
    dt = time.time() - t0
    if r is None:
        print(f"{label:16s} {len(uv):3d} stars -> NO SOLVE ({dt:.1f}s)")
        return
    ra, dec = r["center_radec_deg"]
    extra = ""
    if truth:
        dra = abs((ra - truth[0] + 180) % 360 - 180)
        extra = f"  vs truth dRA={dra:.1f} dDec={dec-truth[1]:+.1f}"
    print(f"{label:16s} {len(uv):3d} stars -> {r['n_inliers']}/{r['n_used']} inliers, "
          f"resid {r['residual_arcsec']:.0f}\", fov {r['fov_deg']:.1f}, layer<={r['layer_mag']}, "
          f"center RA={ra:.1f} Dec={dec:+.1f}{extra} ({dt:.1f}s)")

S = r"C:\Users\Leo\Downloads\aerogaze_test_images\synthetic"
R = r"C:\Users\Leo\Downloads\aerogaze_test_images\real"
print("== ALL SYNTHETIC (reliability) ==")
for nm in ("silver_spring_zenith", "boulder_alt45", "london_alt70", "tokyo_alt30",
           "sydney_zenith", "quito_equator_alt60", "reykjavik_alt80", "capetown_alt50"):
    run(S + f"\\{nm}.jpg", 60, nm)
print("\n== REAL ==")
run(R + r"\orion_constellation.jpg", 100, "orion", truth=(83, 5))
run(R + r"\big_dipper.jpg", 100, "big_dipper", truth=(184, 56))
