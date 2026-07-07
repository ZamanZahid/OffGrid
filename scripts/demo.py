"""AeroGaze end-to-end demo.

Synthesizes a night sky for a known location/time, runs the FULL blind pipeline
(detect -> plate-solve -> gravity fusion -> position), prints the result, and writes:
  demo_output/sky.png        raw synthetic capture
  demo_output/solved.png     annotated solve + recovered position
  android_assets/sky.png     image + capture.json bundle for the on-device demo
  android_assets/capture.json

Usage:  python scripts/demo.py [--lat L --lon O --utc ISO --fov DEG]
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from aerogaze import detect, geometry, pipeline, solve, synth
from aerogaze.catalog import load_hyg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "demo_output")
ASSETS = os.path.join(ROOT, "android_assets")


def err_km(lat1, lon1, lat2, lon2):
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=38.99)     # Silver Spring, MD
    ap.add_argument("--lon", type=float, default=-77.03)
    ap.add_argument("--utc", default="2026-06-26T04:30:00")
    ap.add_argument("--fov", type=float, default=60.0)
    ap.add_argument("--alt", type=float, default=82.0)
    ap.add_argument("--az", type=float, default=35.0)
    ap.add_argument("--roll", type=float, default=18.0)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)

    W, H = 1024, 768
    cat = load_hyg(mag_limit=6.5)
    idx = solve.load_index()

    img, capture, truth = synth.make_capture(
        args.lat, args.lon, args.utc, alt=args.alt, az=args.az, roll=args.roll,
        fov_deg=args.fov, width=W, height=H, cat=cat, seed=11)

    fix = pipeline.solve(capture, img, idx)
    e = err_km(args.lat, args.lon, fix.lat, fix.lon)

    print("=" * 60)
    print("  AeroGaze AI  -  offline celestial positioning")
    print("=" * 60)
    print(f"  true position    : {args.lat:+.4f}, {args.lon:+.4f}")
    print(f"  RECOVERED        : {fix.lat:+.4f}, {fix.lon:+.4f}")
    print(f"  error            : {e:.2f} km")
    print(f"  stars detected   : {fix.n_stars}")
    print(f"  inlier matches   : {fix.n_inliers}")
    print(f"  solve residual   : {fix.residual_arcsec:.1f} arcsec")
    print(f"  sky center (RA/Dec): {fix.zenith_icrs}")
    print("=" * 60)

    _save_visuals(img, capture, idx, args, fix, e, W, H)

    # bundle the on-device demo asset
    from PIL import Image
    Image.fromarray(img).save(os.path.join(ASSETS, "sky.png"))
    with open(os.path.join(ASSETS, "capture.json"), "w") as fh:
        json.dump({**capture, "image": "sky.png",
                   "truth": {"lat": args.lat, "lon": args.lon}}, fh, indent=2)
    print(f"  wrote assets -> {ASSETS}")


def _save_visuals(img, capture, idx, args, fix, e, W, H):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    Image.fromarray(img).save(os.path.join(OUT, "sky.png"))

    uv, _ = detect.detect_stars(img, thresh_sigma=5, max_stars=40)
    res = solve.blind_solve_multiscale(uv, capture["camera"]["fov_deg"], W, H, idx)
    focal = geometry.focal_px_from_fov(capture["camera"]["fov_deg"], W)
    proj, vis = geometry.project(idx.verify_vec, res.R_cam2sky, focal, W, H)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(14, 5.4))
    axL.imshow(img, cmap="gray", origin="upper")
    axL.scatter(proj[vis, 0], proj[vis, 1], s=80, facecolors="none",
                edgecolors="lime", linewidths=0.8, label="catalog (solved)")
    axL.scatter(uv[:, 0], uv[:, 1], s=12, c="red", label="detected")
    axL.set_xlim(0, W); axL.set_ylim(H, 0)
    axL.set_title(f"Plate solve: {fix.n_inliers}/{fix.n_stars} stars matched, "
                  f"resid {fix.residual_arcsec:.0f}\"")
    axL.legend(loc="upper right", fontsize=8)

    _world(axR, args.lat, args.lon, fix.lat, fix.lon, e)
    fig.suptitle("AeroGaze AI - position from a star photo + gravity + clock "
                 "(no GPS / no network)", fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "solved.png"), dpi=120)
    print(f"  wrote visuals -> {OUT}")


def _world(ax, tlat, tlon, glat, glon, e):
    ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
    ax.set_xticks(range(-180, 181, 60)); ax.set_yticks(range(-90, 91, 30))
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="0.6", lw=0.6); ax.axvline(0, color="0.6", lw=0.6)
    ax.scatter([tlon], [tlat], c="lime", s=120, marker="*",
               edgecolors="k", label="true", zorder=5)
    ax.scatter([glon], [glat], c="red", s=60, marker="x",
               label=f"recovered ({e:.1f} km)", zorder=5)
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    ax.set_title("Computed global position")
    ax.legend(loc="lower left", fontsize=8)


if __name__ == "__main__":
    main()
