"""Star detection: a grayscale pixel array -> sub-pixel centroids + fluxes.

Input is a numpy array (on-device, Kotlin decodes the bitmap and passes the array,
so we never need Pillow on the phone). Pure numpy -- no scipy -- so it runs unchanged
inside the Android app under Chaquopy (which then only needs numpy).

Method: robust background + MAD threshold, find local maxima (a pixel >= its 8
neighbours and above threshold), reject lone noise spikes, merge peaks that are too
close, then take a flux-weighted sub-pixel centroid in a small window around each.
"""
from __future__ import annotations

import numpy as np


def _neighbor_max(a):
    """Per-pixel maximum over the 8 neighbours (center excluded), -inf at the border."""
    padded = np.pad(a, 1, mode="constant", constant_values=-np.inf)
    h, w = a.shape
    m = np.full_like(a, -np.inf)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1:
                continue
            m = np.maximum(m, padded[dy:dy + h, dx:dx + w])
    return m


def detect_stars(image, thresh_sigma=5.0, max_stars=40, min_area=2, merge_radius=2.5,
                 window=3):
    """Detect stars in a grayscale image.

    Returns (uv, flux) sorted brightest-first: ``uv`` is (N, 2) of (col, row)
    sub-pixel centroids, ``flux`` is (N,) integrated background-subtracted flux.
    """
    img = np.asarray(image, dtype=float)
    if img.ndim == 3:                                  # collapse colour to luminance
        img = img.mean(axis=2)
    h, w = img.shape

    # robust background + noise via the median and the MAD
    bg = np.median(img)
    mad = np.median(np.abs(img - bg)) + 1e-9
    sigma = 1.4826 * mad
    resid = img - bg
    thresh = thresh_sigma * sigma

    # local maxima above threshold
    peak_mask = (resid > thresh) & (resid >= _neighbor_max(resid))
    ys, xs = np.where(peak_mask)
    if len(ys) == 0:
        return np.empty((0, 2)), np.empty((0,))

    pk = resid[ys, xs]
    order = np.argsort(pk)[::-1]                        # brightest peaks first
    ys, xs, pk = ys[order], xs[order], pk[order]

    half_t = 0.5 * thresh
    cx_l, cy_l, fl_l, py_l, px_l = [], [], [], [], []
    for py, px in zip(ys, xs):
        # reject lone noise spikes: need >= min_area significant pixels in the 3x3
        y0, y1 = max(0, py - 1), min(h, py + 2)
        x0, x1 = max(0, px - 1), min(w, px + 2)
        if (resid[y0:y1, x0:x1] > half_t).sum() < min_area:
            continue
        # drop peaks merged into a brighter, already-accepted one
        if py_l and np.min((np.array(py_l) - py) ** 2 + (np.array(px_l) - px) ** 2) \
                < merge_radius ** 2:
            continue
        # flux-weighted sub-pixel centroid in a window
        wy0, wy1 = max(0, py - window), min(h, py + window + 1)
        wx0, wx1 = max(0, px - window), min(w, px + window + 1)
        win = np.clip(resid[wy0:wy1, wx0:wx1], 0, None)
        rows = np.arange(wy0, wy1)[:, None]
        cols = np.arange(wx0, wx1)[None, :]
        f = win.sum()
        if f <= 0:
            continue
        cy_l.append(float((win * rows).sum() / f))
        cx_l.append(float((win * cols).sum() / f))
        fl_l.append(float(f))
        py_l.append(py)
        px_l.append(px)

    if not fl_l:
        return np.empty((0, 2)), np.empty((0,))
    cx = np.array(cx_l)
    cy = np.array(cy_l)
    flux = np.array(fl_l)
    order = np.argsort(flux)[::-1][:max_stars]
    uv = np.stack([cx[order], cy[order]], axis=1)
    return uv, flux[order]
