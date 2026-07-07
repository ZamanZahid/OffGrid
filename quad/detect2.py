"""Robust star extraction ("cut to just stars"), following astrometry.net's simplexy +
DAOFIND ideas: flatten the sky gradient (subtract a coarse-median background), matched-
filter for point sources, keep sharp/compact local maxima, centroid them, and rank by a
background-subtracted aperture flux (more reliable than a clipped peak on a stretched JPEG).
Prototype uses scipy; the on-device port replaces median/gaussian with pure-numpy versions.
"""
import numpy as np
from scipy import ndimage


def detect_stars2(img, fwhm=2.6, thresh_sigma=4.0, max_stars=150, bg_cell=64,
                  min_sharp=1.3, max_area=80):
    img = np.asarray(img, dtype=float)
    if img.ndim == 3:
        img = img.mean(axis=2)
    h, w = img.shape

    # 1) background: coarse block-median, bilinearly upsampled, then subtract
    nh, nw = max(1, h // bg_cell), max(1, w // bg_cell)
    sm = np.empty((nh, nw))
    ys = np.linspace(0, h, nh + 1).astype(int)
    xs = np.linspace(0, w, nw + 1).astype(int)
    for i in range(nh):
        for j in range(nw):
            sm[i, j] = np.median(img[ys[i]:ys[i + 1], xs[j]:xs[j + 1]])
    bg = ndimage.zoom(sm, (h / nh, w / nw), order=1)[:h, :w]
    flat = img - bg

    # 2) noise from the flattened image (MAD)
    sigma = 1.4826 * np.median(np.abs(flat - np.median(flat))) + 1e-6
    thr = thresh_sigma * sigma

    # 3) matched filter (Gaussian ~ stellar PSF) then local maxima above threshold
    conv = ndimage.gaussian_filter(flat, fwhm / 2.355)
    mx = ndimage.maximum_filter(conv, size=3)
    peak = (conv == mx) & (conv > thr)

    # 4) reject extended blobs (clouds/nebulosity/foreground): connected-component area
    lbl, n = ndimage.label(flat > thr)
    if n:
        areas = ndimage.sum(np.ones_like(flat), lbl, np.arange(1, n + 1))
        big = np.zeros(n + 1, bool)
        big[1:] = areas > max_area
        peak &= ~big[lbl]

    pys, pxs = np.where(peak)
    cents, fluxes = [], []
    for py, px in zip(pys, pxs):
        # sharpness: peak vs local mean (point sources are peaky; reject flat/extended)
        y0, y1 = max(0, py - 2), min(h, py + 3)
        x0, x1 = max(0, px - 2), min(w, px + 3)
        ring = flat[y0:y1, x0:x1]
        if ring.size < 9 or flat[py, px] < min_sharp * ring.mean():
            continue
        # background-subtracted aperture flux + flux-weighted centroid (7x7)
        ay0, ay1 = max(0, py - 3), min(h, py + 4)
        ax0, ax1 = max(0, px - 3), min(w, px + 4)
        ap = np.clip(flat[ay0:ay1, ax0:ax1], 0, None)
        f = float(ap.sum())
        if f <= 0:
            continue
        ry = np.arange(ay0, ay1)[:, None]
        rx = np.arange(ax0, ax1)[None, :]
        cents.append((float((ap * rx).sum() / f), float((ap * ry).sum() / f)))
        fluxes.append(f)

    if not fluxes:
        return np.empty((0, 2)), np.empty(0)
    cents = np.array(cents)
    fluxes = np.array(fluxes)
    order = np.argsort(fluxes)[::-1][:max_stars]
    return cents[order], fluxes[order]
