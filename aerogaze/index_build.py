"""Build the catalog hash index for blind plate-solving.

The index is two things:
* a **matching** subset of bright stars with a table of all star *pairs* within the
  camera field of view, keyed by angular separation (the rotation-invariant we match);
* a deeper **verification** catalog used to count inliers once an orientation is found.

The result is saved as a single ``.npz`` that ships as an Android asset. Built once on
the laptop.
"""
from __future__ import annotations

import os

import numpy as np
from scipy.spatial import cKDTree

from . import geometry
from .catalog import load_hyg

_DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "..", "data", "index.npz")


def build_index(out=None, index_mag=5.5, verify_mag=7.0, max_sep_deg=80.0, cat=None):
    """Build and save the index.

    Parameters
    ----------
    index_mag : float
        Magnitude limit for the bright stars used to form matching pairs/triangles.
    verify_mag : float
        Deeper limit for the verification catalog (inlier counting).
    max_sep_deg : float
        Largest star-pair separation stored. Must exceed the camera's diagonal FOV.
    """
    if out is None:
        out = _DEFAULT_OUT
    cat_v = cat if cat is not None else load_hyg(mag_limit=verify_mag)

    mmask = cat_v.mag <= index_mag
    match_vec = cat_v.vec[mmask].astype(np.float64)
    match_mag = cat_v.mag[mmask].astype(np.float32)
    match_ids = cat_v.ids[mmask].astype(np.int64)

    # all bright-star pairs within max_sep, sorted by angular separation
    tree = cKDTree(match_vec)
    chord = 2.0 * np.sin(np.radians(max_sep_deg) / 2.0)
    pairs = tree.query_pairs(chord, output_type="ndarray")          # (P, 2) ints
    seps = geometry.angsep(match_vec[pairs[:, 0]], match_vec[pairs[:, 1]])
    order = np.argsort(seps)

    np.savez_compressed(
        out,
        match_vec=match_vec.astype(np.float32),
        match_mag=match_mag,
        match_ids=match_ids,
        verify_vec=cat_v.vec.astype(np.float32),
        verify_mag=cat_v.mag.astype(np.float32),
        pair_a=pairs[order, 0].astype(np.int32),
        pair_b=pairs[order, 1].astype(np.int32),
        pair_sep=seps[order].astype(np.float64),
        meta=np.array([index_mag, verify_mag, max_sep_deg], dtype=np.float64),
    )
    size_mb = os.path.getsize(out) / 1e6
    print(f"Index: {len(match_vec)} match stars, {len(cat_v.vec)} verify stars, "
          f"{len(pairs)} pairs, max_sep={max_sep_deg}deg -> {out} ({size_mb:.1f} MB)")
    return out


if __name__ == "__main__":
    build_index()
