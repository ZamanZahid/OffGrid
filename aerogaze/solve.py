"""Blind plate solver: detected star pixels -> camera orientation in the sky.

Algorithm (the "angle method" + triangle voting + Wahba + RANSAC verification):

1. Because the FOV (hence pixel scale) is known, each detected star maps to a bearing
   unit vector in the camera frame, and the angle between any two detected stars is
   measurable directly -- a rotation-invariant fingerprint.
2. Take the brightest detected stars; for triangles among them, look up catalog star
   pairs/triangles whose three angular separations match (within tolerance).
3. A matched triangle gives a 3-star correspondence; solve Wahba's problem (SVD) for
   the rotation ``R_cam2sky``.
4. Verify by projecting the whole catalog and counting inlier detections; keep the
   orientation with the most inliers, then refine on all inliers.

Pure numpy (no scipy), so it runs on-device under Chaquopy with only numpy.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from . import geometry

_DEFAULT_INDEX = os.path.join(os.path.dirname(__file__), "..", "data", "index.npz")


@dataclass
class SolveResult:
    R_cam2sky: np.ndarray
    n_inliers: int
    residual_arcsec: float
    center_radec_deg: tuple


class Index:
    """Loaded catalog index with per-star neighbour adjacency for triangle search."""

    def __init__(self, npz):
        self.match_vec = npz["match_vec"].astype(np.float64)
        self.match_mag = npz["match_mag"]
        self.match_ids = npz["match_ids"]
        self.verify_vec = npz["verify_vec"].astype(np.float64)
        self.verify_mag = npz["verify_mag"]
        self.pair_sep = npz["pair_sep"].astype(np.float64)
        pair_a = npz["pair_a"].astype(np.int64)
        pair_b = npz["pair_b"].astype(np.int64)
        self.index_mag, self.verify_mag_limit, self.max_sep = npz["meta"]

        # global sorted pair list (by separation) for seeding an edge
        self._pa, self._pb = pair_a, pair_b

        # directed neighbour CSR, each star's neighbours sorted by separation
        a = np.concatenate([pair_a, pair_b])
        b = np.concatenate([pair_b, pair_a])
        s = np.concatenate([self.pair_sep, self.pair_sep])
        order = np.lexsort((s, a))                       # by star, then separation
        self._nbr_star = a[order]
        self._nbr_idx = b[order]
        self._nbr_sep = s[order]
        n = len(self.match_vec)
        self._off = np.searchsorted(self._nbr_star, np.arange(n + 1))

    # -- catalog pair lookups ------------------------------------------------ #
    def pairs_with_sep(self, sep, tol):
        """Indices of catalog pairs whose separation is within [sep-tol, sep+tol]."""
        lo = np.searchsorted(self.pair_sep, sep - tol, side="left")
        hi = np.searchsorted(self.pair_sep, sep + tol, side="right")
        return self._pa[lo:hi], self._pb[lo:hi]

    def neighbors_with_sep(self, star, sep, tol):
        """Catalog stars at angular separation ~sep from ``star``."""
        lo = self._off[star]
        hi = self._off[star + 1]
        seg_sep = self._nbr_sep[lo:hi]
        i = np.searchsorted(seg_sep, sep - tol, side="left")
        j = np.searchsorted(seg_sep, sep + tol, side="right")
        return self._nbr_idx[lo + i:lo + j]


def load_index(path=None):
    if path is None:
        path = _DEFAULT_INDEX
    return Index(np.load(path))


# --------------------------------------------------------------------------- #
# core geometry helpers
# --------------------------------------------------------------------------- #
def _wahba(bearings, sky):
    """Least-squares rotation R with sky_n ~= R @ bearing_n (Kabsch/Wahba via SVD)."""
    H = sky.T @ bearings
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(U @ Vt))
    D = np.diag([1.0, 1.0, d])
    return U @ D @ Vt


def _verify(R, uv_detected, index, focal, width, height, pixel_tol):
    """Project the catalog under R; count detected stars matched within pixel_tol."""
    proj, vis = geometry.project(index.verify_vec, R, focal, width, height)
    pv = proj[vis]
    vidx = np.where(vis)[0]
    if len(pv) == 0:
        return 0, np.array([], int), np.array([], int), float("inf")
    # nearest projected catalog star to each detection (brute force; sizes are small)
    diff = uv_detected[:, None, :] - pv[None, :, :]
    d2 = np.einsum("ijk,ijk->ij", diff, diff)
    j = np.argmin(d2, axis=1)
    d = np.sqrt(d2[np.arange(len(uv_detected)), j])
    hit = d <= pixel_tol
    det_idx = np.where(hit)[0]
    cat_idx = vidx[j[hit]]
    resid = float(np.degrees(np.median(d[hit]) / focal) * 3600.0) if hit.any() else float("inf")
    return int(hit.sum()), det_idx, cat_idx, resid


def blind_solve(uv, fov_deg, width, height, index,
                n_bright=10, pixel_tol=2.5, lookup_tol_px=3.0,
                min_inliers=8, strong_inliers=0.6, min_edge_deg=1.5,
                verify_budget=400):
    """Identify the sky. Returns a :class:`SolveResult` or ``None`` if it fails.

    ``uv`` are detected star pixels sorted brightest-first. Strategy: for triangles
    among the brightest detections (tried bright-first), anchor each catalog star as
    the triangle's apex and intersect its neighbour-by-distance sets -- this prunes
    thousands of catalog candidates down to a few, then Wahba + verify confirms.
    """
    uv = np.asarray(uv, dtype=float)
    N = len(uv)
    if N < 4:
        return None
    focal = geometry.focal_px_from_fov(fov_deg, width)
    bearings = geometry.unproject(uv, np.eye(3), focal, width, height)   # camera frame
    tol = lookup_tol_px / focal                                          # radians
    min_edge = np.radians(min_edge_deg)
    strong = max(min_inliers, int(strong_inliers * N))

    m = min(n_bright, N)
    ang = np.zeros((m, m))
    for i in range(m):
        for j in range(i + 1, m):
            ang[i, j] = ang[j, i] = geometry.angsep(bearings[i], bearings[j])

    # triangles, brightest-first (low detection indices = bright real stars)
    tris = sorted(combinations(range(m), 3), key=lambda t: t[0] + t[1] + t[2])

    best = None
    budget = verify_budget
    for (i, j, k) in tris:
        # apex p = vertex opposite the longest edge -> its two edges are the two
        # smallest (fewest catalog neighbours -> tightest pruning).
        edges = sorted([(ang[i, j], i, j), (ang[i, k], i, k), (ang[j, k], j, k)])
        (e_qr, q, r) = edges[2]                          # longest edge endpoints
        p = ({i, j, k} - {q, r}).pop()
        th_pq, th_pr = ang[p, q], ang[p, r]
        if min(th_pq, th_pr, e_qr) < min_edge:
            continue

        for ca in range(len(index.match_vec)):           # apex candidate
            Q = index.neighbors_with_sep(ca, th_pq, tol)
            if len(Q) == 0:
                continue
            Rset = index.neighbors_with_sep(ca, th_pr, tol)
            if len(Rset) == 0:
                continue
            Rset = set(Rset.tolist())
            bear = bearings[[p, q, r]]
            for cb in Q:                                 # q candidate
                for cr in index.neighbors_with_sep(cb, e_qr, tol):
                    if cr not in Rset:                   # r must close the triangle
                        continue
                    R = _wahba(bear, index.match_vec[[ca, cb, cr]])
                    n_in, det_i, cat_i, resid = _verify(
                        R, uv, index, focal, width, height, pixel_tol)
                    budget -= 1
                    if best is None or n_in > best[0]:
                        best = (n_in, R, det_i, cat_i, resid)
                    if n_in >= strong:
                        return _finalize(best, uv, index, focal, width, height, pixel_tol)
                    if budget <= 0:
                        break
                if budget <= 0:
                    break
            if budget <= 0:
                break
        if budget <= 0:
            break

    if best is None or best[0] < min_inliers:
        return None
    return _finalize(best, uv, index, focal, width, height, pixel_tol)


def blind_solve_multiscale(uv, fov_deg, width, height, index,
                           scale_range=0.025, n_scales=21, **kw):
    """Blind solve robust to camera-scale (FOV) uncertainty.

    Sweeps the assumed FOV by +-``scale_range`` around nominal (nominal first, then
    outward) and keeps the orientation with the most inliers -- which also identifies
    the true focal length. Early-exits as soon as a strong solution appears, so a
    correctly-calibrated camera still solves in one shot.
    """
    uv = np.asarray(uv, dtype=float)
    N = len(uv)
    strong = max(kw.get("min_inliers", 8), int(kw.get("strong_inliers", 0.6) * N))
    fracs = np.linspace(-scale_range, scale_range, n_scales)
    fracs = fracs[np.argsort(np.abs(fracs))]             # nominal first, then outward
    best = None
    for f in fracs:
        res = blind_solve(uv, fov_deg * (1.0 + f), width, height, index, **kw)
        if res is not None and (best is None or res.n_inliers > best.n_inliers):
            best = res
        if best is not None and best.n_inliers >= strong:
            return best
    return best


def _finalize(best, uv, index, focal, width, height, pixel_tol):
    """Refine the winning orientation on all inliers and package the result."""
    n_in, R, det_i, cat_i, resid = best
    if len(det_i) >= 3:
        bear = geometry.unproject(uv[det_i], np.eye(3), focal, width, height)
        R = _wahba(bear, index.verify_vec[cat_i])
        n_in, det_i, cat_i, resid = _verify(R, uv, index, focal, width, height, pixel_tol)
    center = geometry.unproject(np.array([[width / 2.0, height / 2.0]]),
                                R, focal, width, height)[0]
    ra, dec = geometry.vec_to_radec(center)
    return SolveResult(R_cam2sky=R, n_inliers=int(n_in), residual_arcsec=resid,
                       center_radec_deg=(float(np.degrees(ra)), float(np.degrees(dec))))
