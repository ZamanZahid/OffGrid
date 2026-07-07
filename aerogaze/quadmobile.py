"""Numpy-ONLY quad-hash solver for on-device (Chaquopy). Same algorithm as quadsolve.py
but with every scipy.cKDTree replaced by numpy: a 4D grid-hash for the code lookup and
brute force (over <=90 detected stars / a few hundred projected stars) for neighbours,
circle membership, and verification. The catalog index is precomputed on the laptop and
shipped as .npz assets; this module only does the image side + matching.
"""
from __future__ import annotations

import itertools

import numpy as np

from . import geometry

IMG_RANKS = tuple(range(1, 19))


def quad_code(pts):
    best, ab = -1.0, None
    for i, j in itertools.combinations(range(4), 2):
        d = float(np.sum((pts[i] - pts[j]) ** 2))
        if d > best:
            best, ab = d, (i, j)
    a, b = ab
    cd = [k for k in range(4) if k not in ab]
    A, B = pts[a], pts[b]
    v = B - A
    n2 = float(v @ v)
    if n2 < 1e-12:
        return None
    Ma, Mb = (v[0] + v[1]) / n2, (v[1] - v[0]) / n2
    M = np.array([[Ma, Mb], [-Mb, Ma]])
    c0, c1 = M @ (pts[cd[0]] - A), M @ (pts[cd[1]] - A)
    ci, di = cd
    if c0[0] > c1[0]:
        c0, c1, ci, di = c1, c0, di, ci
    if c0[0] + c1[0] > 1.0:
        c0, c1 = np.array([1.0, 1.0]) - c0, np.array([1.0, 1.0]) - c1
        a, b = b, a
        if c0[0] > c1[0]:
            c0, c1, ci, di = c1, c0, di, ci
    code = np.array([c0[0], c0[1], c1[0], c1[1]])
    if not np.all(np.isfinite(code)):
        return None
    return code, [a, b, ci, di]


class QuadLayer:
    """A precomputed catalog layer + a numpy 4D grid-hash over its quad codes."""

    def __init__(self, npz_path, cell=0.01):
        z = np.load(npz_path)
        self.bvec = z["bvec"].astype(np.float64)
        self.verify_vec = z["verify_vec"].astype(np.float64)
        self.codes = z["codes"].astype(np.float64)
        self.quads = z["quads"]
        self.match_mag = float(z["match_mag"]) if "match_mag" in z.files else 0.0
        self.cell = cell
        keys = np.floor(self.codes / cell).astype(np.int64)
        grid = {}
        for i in range(len(keys)):
            grid.setdefault((int(keys[i, 0]), int(keys[i, 1]),
                             int(keys[i, 2]), int(keys[i, 3])), []).append(i)
        self.grid = {k: np.array(v, dtype=np.int64) for k, v in grid.items()}

    def query(self, code, code_tol):
        base = np.floor(code / self.cell).astype(np.int64)
        cand = []
        for off in itertools.product((-1, 0, 1), repeat=4):
            k = (int(base[0] + off[0]), int(base[1] + off[1]),
                 int(base[2] + off[2]), int(base[3] + off[3]))
            g = self.grid.get(k)
            if g is not None:
                cand.append(g)
        if not cand:
            return np.empty(0, np.int64)
        cand = np.concatenate(cand)
        d = np.linalg.norm(self.codes[cand] - code, axis=1)
        return cand[d <= code_tol]


def load_layers(paths, cell=0.01):
    return [QuadLayer(p, cell) for p in paths]


def _knn_order(uv):
    d2 = ((uv[:, None, :] - uv[None, :, :]) ** 2).sum(-1)
    return np.argsort(d2, axis=1)            # nearest-first (self at col 0)


def _wahba(bearings, sky):
    H = sky.T @ bearings
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(U @ Vt))
    return U @ np.diag([1.0, 1.0, d]) @ Vt


def _nearest_px(uv, pv):
    d2 = ((uv[:, None, :] - pv[None, :, :]) ** 2).sum(-1)
    return np.sqrt(d2.min(axis=1))


def _verify(R, focal, uv, vvec, w, h, pixel_tol):
    proj, vis = geometry.project(vvec, R, focal, w, h)
    pv = proj[vis]
    if len(pv) < 1:
        return 0, float("inf"), float("inf")
    d = _nearest_px(uv, pv)
    hit = d <= pixel_tol
    if not hit.any():
        return 0, float("inf"), float("inf")
    rpx = float(np.median(d[hit]))
    return int(hit.sum()), float(np.degrees(rpx / focal) * 3600.0), rpx


def _nearest_idx(uv, pv):
    d2 = ((uv[:, None, :] - pv[None, :, :]) ** 2).sum(-1)
    return np.sqrt(d2.min(axis=1)), d2.argmin(axis=1)


def _refine(R, focal, uv, vvec, w, h, pixel_tol, iters=6):
    cx, cy = w / 2.0, h / 2.0
    for _ in range(iters):
        proj, vis = geometry.project(vvec, R, focal, w, h)
        pv, vidx = proj[vis], np.where(vis)[0]
        if len(pv) < 4:
            break
        d, j = _nearest_idx(uv, pv)
        hit = d <= pixel_tol
        if hit.sum() < 4:
            break
        uvh, catv = uv[hit], vvec[vidx[j[hit]]]
        R = _wahba(geometry.unproject(uvh, np.eye(3), focal, w, h), catv)
        cam = catv @ R
        zc = cam[:, 2]
        ok = zc > 1e-6
        if ok.sum() >= 4:
            ax, ay = cam[ok, 0] / zc[ok], cam[ok, 1] / zc[ok]
            du, dv = uvh[ok, 0] - cx, -(uvh[ok, 1] - cy)
            den = float(np.sum(ax * ax + ay * ay))
            if den > 1e-9:
                focal = float(np.sum(du * ax + dv * ay) / den)
    n_in, resid_as, rpx = _verify(R, focal, uv, vvec, w, h, pixel_tol)
    return R, focal, n_in, resid_as, rpx


def _img_quads(uv, neg_mag, order, ranks=IMG_RANKS, brightest_m=4):
    n = len(uv)
    for a in range(n):
        nbrs = order[a, 1:]
        seen = set()
        for rk in ranks:
            if rk - 1 >= len(nbrs):
                continue
            b = int(nbrs[rk - 1])
            if b <= a or b in seen:
                continue
            seen.add(b)
            mid = (uv[a] + uv[b]) / 2.0
            radius = float(np.linalg.norm(uv[a] - uv[b])) / 2.0
            dist = np.linalg.norm(uv - mid, axis=1)
            inside = [c for c in np.where(dist <= radius)[0] if c != a and c != b]
            if len(inside) < 2:
                continue
            inside.sort(key=lambda c: neg_mag[c])
            for c_, d_ in itertools.combinations(inside[:brightest_m], 2):
                yield [a, b, c_, d_]


def solve_one(uv, flux, w, h, layer, code_tol=0.012, pixel_tol=2.0, resid_px_max=1.8,
              resid_arcsec_max=150.0, raw_arcsec_max=800.0):
    uv = np.asarray(uv, float)
    N = len(uv)
    if N < 4:
        return None
    cx, cy = w / 2.0, h / 2.0
    xy = np.column_stack([uv[:, 0] - cx, -(uv[:, 1] - cy)])
    order = _knn_order(uv)
    neg_mag = -np.asarray(flux, float)
    best = None
    for four in _img_quads(uv, neg_mag, order):
        qc = quad_code(xy[four])
        if qc is None:
            continue
        code, ordr = qc
        for qj in layer.query(code, code_tol):
            img_pts = uv[[four[o] for o in ordr]]
            cat_vec = layer.bvec[layer.quads[qj]]
            cat_ab = geometry.angsep(cat_vec[0], cat_vec[1])
            img_ab = float(np.linalg.norm(img_pts[0] - img_pts[1]))
            if cat_ab < 1e-9 or img_ab < 1e-6:
                continue
            focal = img_ab / cat_ab
            fov = geometry.fov_deg_from_focal(focal, w)
            if fov < 4.0 or fov > 130.0:
                continue
            R = _wahba(geometry.unproject(img_pts, np.eye(3), focal, w, h), cat_vec)
            n_in, resid_as, rpx = _verify(R, focal, uv, layer.verify_vec, w, h, pixel_tol)
            # LOOSE pre-refine gate: a raw 4-star quad fit hasn't had its focal/rotation
            # refined yet, so its residual is naturally larger -- only discard wildly-off
            # (wrong-scale) raw matches here. The STRICT residual gate runs *after*
            # refinement (below); applying it here rejected every good candidate before it
            # could be refined, which is what broke uploaded (JPEG) skies.
            if resid_as > raw_arcsec_max:
                continue
            if best is None or n_in > best[0]:
                best = (n_in, R, focal)
    if best is None:
        return None
    R, fr, n_in, resid_as, rpx = _refine(best[1], best[2], uv, layer.verify_vec, w, h, pixel_tol)
    if rpx > resid_px_max:
        n_in, R, fr = best[0], best[1], best[2]
        _, _, n_in, resid_as, rpx = _refine(R, fr, uv, layer.verify_vec, w, h, pixel_tol)
    if resid_as > resid_arcsec_max:
        return None
    c = geometry.unproject(np.array([[cx, cy]]), R, fr, w, h)[0]
    ra, dec = geometry.vec_to_radec(c)
    return {"R_cam2sky": R, "focal": float(fr), "n_inliers": int(n_in),
            "n_stars": int(N), "residual_arcsec": float(resid_as),
            "fov_deg": float(geometry.fov_deg_from_focal(fr, w)),
            "center_radec_deg": (float(np.degrees(ra)), float(np.degrees(dec)))}


def solve(uv, flux, w, h, layers, K_list=(15, 25, 40, 60, 90), min_inliers=12, **kw):
    uv = np.asarray(uv, float)
    flux = np.asarray(flux, float)
    best = None
    for layer in layers:
        for K in K_list:
            if K < 8:
                continue
            m = min(K, len(uv))
            r = solve_one(uv[:m], flux[:m], w, h, layer, **kw)
            if r is None:
                continue
            if best is None or r["n_inliers"] > best["n_inliers"]:
                best = r
            if r["n_inliers"] >= max(min_inliers, int(0.45 * m)):
                return best
    if best is not None and best["n_inliers"] >= min_inliers:
        return best
    return None
