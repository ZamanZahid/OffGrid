import sys, time
sys.path.insert(0, r"C:\Users\Leo\BlairHacks"); sys.path.insert(0, r"C:\Users\Leo\BlairHacks\quad")
import numpy as np
from PIL import Image
from aerogaze import detect
import quadmobile  # numpy ONLY

cache = r"C:\Users\Leo\BlairHacks\quad\cache"
paths = [f"{cache}\\idx_v6union_m{m}_v7.5.npz" for m in (4.5, 5.5, 6.5)]
t = time.time()
layers = quadmobile.load_layers(paths, cell=0.013)
print(f"loaded {len(layers)} layers (numpy grid-hash) in {time.time()-t:.1f}s, "
      f"quads: {[len(l.codes) for l in layers]}")

S = r"C:\Users\Leo\Downloads\aerogaze_test_images\synthetic"
names = ("silver_spring_zenith", "boulder_alt45", "london_alt70", "tokyo_alt30",
         "sydney_zenith", "quito_equator_alt60", "reykjavik_alt80", "capetown_alt50")
ok = 0
for nm in names:
    g = np.asarray(Image.open(f"{S}\\{nm}.jpg").convert("L"))
    h, w = g.shape
    uv, flux = detect.detect_stars(g, max_stars=60, thresh_sigma=4.0)
    t0 = time.time()
    r = quadmobile.solve(uv, flux, w, h, layers)
    dt = time.time() - t0
    if r:
        ok += 1
        print(f"{nm:22s} {r['n_inliers']}/{r['n_stars']} inliers, resid "
              f"{r['residual_arcsec']:.0f}\", fov {r['fov_deg']:.1f} ({dt:.2f}s)")
    else:
        print(f"{nm:22s} NO SOLVE ({dt:.2f}s)")
print(f"\nnumpy-only: {ok}/8 solved")
