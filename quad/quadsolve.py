"""Geometric quad-hash blind solver (astrometry.net-style), laptop proof of concept.

Brightness-independent *matching* via 4-star geometric hash codes. The key to RELIABLE
matching is CANONICAL quads: for a star pair (A,B), the other two stars are the two
BRIGHTEST inside the circle of diameter AB. The image and the catalog then pick the SAME
four stars, so their codes agree. Several magnitude-depth layers handle the unknown
limiting magnitude; scale (FOV) falls out of each match, so there is no FOV sweep.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, r"C:\Users\Leo\BlairHacks")

import numpy as np
from scipy.spatial import cKDTree

from aerogaze import geometry
from aerogaze.catalog import load_hyg

CACHE = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE, exist_ok=True)
VERSION = "v6union"


def tangent_project(vecs, center):
    z = geometry.normalize(center)
    ref = np.array([0.0, 0.0, 1.0]) if abs(z[2]) < 0.99 else np.array([1.0, 0.0, 0.0])
    x = geometry.normalize(np.cross(ref, z))
    y = np.cross(z, x)
    d = vecs @ z
    return np.stack([(vecs @ x) / d, (vecs @ y) / d], axis=-1)


def quad_code(pts):
    """4 points (4,2) -> (code[4], order[4]) or None. A,B = widest pair (the AB circle
    diameter), mapped to (0,0),(1,1); C,D are the code. Symmetry: xC<=xD, xC+xD<=1."""
    import itertools
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


CAT_SCALES_DEG = (2.0, 3.5, 6.0, 10.0, 17.0, 28.0, 45.0)


def canonical_quads(vecs, mag, tree, scales_deg=CAT_SCALES_DEG, brightest_m=4, n_query=80):
    """Yield catalog quads at MULTIPLE SCALES. For each star A, pick the neighbour B
    nearest each target angular separation, then form quads (A,B, pairs among the
    brightest_m stars inside the AB circle). Multi-scale so any field FOV has a match."""
    import itertools
    n = len(vecs)
    nq = min(n_query + 1, n)
    for a in range(n):
        d, nn = tree.query(vecs[a], k=nq)
        d, nbrs = np.atleast_1d(d)[1:], np.atleast_1d(nn)[1:]
        seps = np.degrees(2.0 * np.arcsin(np.clip(d / 2.0, 0.0, 1.0)))
        if len(seps) == 0:
            continue
        # B candidates: nearest few (reliable small-scale quads) + one per angular scale
        # bin (multi-scale reach). Union covers both wide and narrow fields.
        b_bins = list(range(min(3, len(nbrs)))) + \
            [int(np.argmin(np.abs(seps - s))) for s in scales_deg]
        seen = set()
        for bi in dict.fromkeys(b_bins):
            b = int(nbrs[bi])
            if b <= a or b in seen:
                continue
            seen.add(b)
            radius = geometry.angsep(vecs[a], vecs[b]) / 2.0
            mid = geometry.normalize((vecs[a] + vecs[b]) / 2.0)
            inside = [c for c in tree.query_ball_point(mid, 2.0 * np.sin(radius / 2.0))
                      if c != a and c != b]
            if len(inside) < 2:
                continue
            inside.sort(key=lambda c: mag[c])
            for c_, d_ in itertools.combinations(inside[:brightest_m], 2):
                yield [a, b, c_, d_]


class QuadIndex:
    def __init__(self, match_mag, verify_mag=7.5):
        self.match_mag, self.verify_mag = match_mag, verify_mag
        path = os.path.join(CACHE, f"idx_{VERSION}_m{match_mag}_v{verify_mag}.npz")
        if os.path.exists(path):
            z = np.load(path)
            self.bvec, self.verify_vec = z["bvec"], z["verify_vec"]
            self.codes, self.quads = z["codes"], z["quads"]
        else:
            self._build(); np.savez_compressed(
                path, bvec=self.bvec, verify_vec=self.verify_vec,
                codes=self.codes, quads=self.quads)
        self.code_tree = cKDTree(self.codes)
        print(f"  layer mag<={match_mag}: {len(self.bvec)} stars, {len(self.codes)} quads")

    def _build(self):
        cat = load_hyg(mag_limit=self.verify_mag)
        self.verify_vec = cat.vec.astype(np.float64)
        bmask = cat.mag <= self.match_mag
        self.bvec = cat.vec[bmask].astype(np.float64)
        bmag = cat.mag[bmask]
        tree = cKDTree(self.bvec)
        codes, quads = [], []
        for four in canonical_quads(self.bvec, bmag, tree):
            pts = tangent_project(self.bvec[four], self.bvec[four].mean(0))
            qc = quad_code(pts)
            if qc is not None:
                codes.append(qc[0]); quads.append([four[o] for o in qc[1]])
        self.codes = np.array(codes)
        self.quads = np.array(quads, dtype=np.int32)


def build_layers(mags=(4.5, 5.5, 6.5), verify_mag=7.5):
    print("building/loading layers...")
    return [QuadIndex(m, verify_mag) for m in mags]


def _wahba(bearings, sky):
    H = sky.T @ bearings
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(U @ Vt))
    return U @ np.diag([1.0, 1.0, d]) @ Vt


def _verify(R, focal, uv, idx, w, h, pixel_tol):
    proj, vis = geometry.project(idx.verify_vec, R, focal, w, h)
    pv = proj[vis]
    if len(pv) < 1:
        return 0, float("inf"), float("inf")
    d, _ = cKDTree(pv).query(uv, k=1)
    hit = d <= pixel_tol
    if not hit.any():
        return 0, float("inf"), float("inf")
    rpx = float(np.median(d[hit]))
    return int(hit.sum()), float(np.degrees(rpx / focal) * 3600.0), rpx


def _refine(R, focal, uv, idx, w, h, pixel_tol, iters=6):
    """Alternate Wahba (R) and a linear least-squares for focal on all matched inliers.
    Refining focal as well as R is what tightens the solution and recovers the full set
    of inlier stars (a 1% scale error alone drops the outer half of the field)."""
    cx, cy = w / 2.0, h / 2.0
    for _ in range(iters):
        proj, vis = geometry.project(idx.verify_vec, R, focal, w, h)
        pv, vidx = proj[vis], np.where(vis)[0]
        if len(pv) < 4:
            break
        d, j = cKDTree(pv).query(uv, k=1)
        hit = d <= pixel_tol
        if hit.sum() < 4:
            break
        uvh, catv = uv[hit], idx.verify_vec[vidx[j[hit]]]
        R = _wahba(geometry.unproject(uvh, np.eye(3), focal, w, h), catv)
        cam = catv @ R                                   # sky -> camera
        zc = cam[:, 2]
        ok = zc > 1e-6
        if ok.sum() >= 4:
            ax, ay = cam[ok, 0] / zc[ok], cam[ok, 1] / zc[ok]
            du, dv = uvh[ok, 0] - cx, -(uvh[ok, 1] - cy)
            den = float(np.sum(ax * ax + ay * ay))
            if den > 1e-9:
                focal = float(np.sum(du * ax + dv * ay) / den)
    n_in, resid_as, rpx = _verify(R, focal, uv, idx, w, h, pixel_tol)
    return R, focal, n_in, resid_as, rpx


def solve_one(uv, flux, w, h, idx, code_tol=0.012, pixel_tol=2.0, resid_px_max=1.8):
    """Best resid-gated candidate from one layer using canonical image quads, or None."""
    uv = np.asarray(uv, float)
    flux = np.asarray(flux, float)
    N = len(uv)
    if N < 4:
        return None
    cx, cy = w / 2.0, h / 2.0
    xy = np.column_stack([uv[:, 0] - cx, -(uv[:, 1] - cy)])      # y-up to match catalog
    tree = cKDTree(uv)
    neg_mag = -flux                                              # brightest = highest flux
    best = None
    for four in canonical_quads_img(uv, neg_mag, tree):
        qc = quad_code(xy[four])
        if qc is None:
            continue
        code, order = qc
        dd, jj = idx.code_tree.query(code, k=5, distance_upper_bound=code_tol)
        for dist, qj in zip(np.atleast_1d(dd), np.atleast_1d(jj)):
            if not np.isfinite(dist) or qj >= len(idx.quads):
                continue
            img_pts = uv[[four[o] for o in order]]
            cat_vec = idx.bvec[idx.quads[qj]]
            cat_ab = geometry.angsep(cat_vec[0], cat_vec[1])
            img_ab = float(np.linalg.norm(img_pts[0] - img_pts[1]))
            if cat_ab < 1e-9 or img_ab < 1e-6:
                continue
            focal = img_ab / cat_ab
            fov = geometry.fov_deg_from_focal(focal, w)
            if fov < 4.0 or fov > 130.0:
                continue
            R = _wahba(geometry.unproject(img_pts, np.eye(3), focal, w, h), cat_vec)
            n_in, resid_as, rpx = _verify(R, focal, uv, idx, w, h, pixel_tol)
            if rpx > resid_px_max:
                continue
            if best is None or n_in > best["n_inliers"]:
                best = {"R": R, "focal": float(focal), "n_inliers": int(n_in),
                        "residual_arcsec": resid_as, "n_used": N}
    if best is None:
        return None
    R, fr, n_in, resid_as, rpx = _refine(best["R"], best["focal"], uv, idx, w, h, pixel_tol)
    if rpx <= resid_px_max and n_in >= best["n_inliers"]:
        best.update(R=R, focal=float(fr), n_inliers=int(n_in), residual_arcsec=resid_as)
    c = geometry.unproject(np.array([[cx, cy]]), best["R"], best["focal"], w, h)[0]
    ra, dec = geometry.vec_to_radec(c)
    best["center_radec_deg"] = (float(np.degrees(ra)), float(np.degrees(dec)))
    best["fov_deg"] = float(geometry.fov_deg_from_focal(best["focal"], w))
    return best


IMG_RANKS = tuple(range(1, 19))   # dense: the image has few stars, so try every near B


def canonical_quads_img(uv, neg_mag, tree, ranks=IMG_RANKS, brightest_m=8):
    """Image quads at MULTIPLE SCALES: B = the rank-th nearest neighbour (geometric ranks),
    then pairs among the brightest_m by flux inside the AB circle. The scale-invariant
    code bridges the image's pixel scales to the catalog's angular scales (unknown FOV)."""
    import itertools
    n = len(uv)
    kmax = min(max(ranks) + 1, n)
    for a in range(n):
        _, nn = tree.query(uv[a], k=kmax)
        nbrs = np.atleast_1d(nn)[1:]
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
            inside = [c for c in tree.query_ball_point(mid, radius) if c != a and c != b]
            if len(inside) < 2:
                continue
            inside.sort(key=lambda c: neg_mag[c])
            for c_, d_ in itertools.combinations(inside[:brightest_m], 2):
                yield [a, b, c_, d_]


# --------------------------------------------------------------------------- #
# radial-distortion-aware solve (for wide real lenses)
# --------------------------------------------------------------------------- #
def _project_dist(vvec, R, focal, k1, k2, w, h):
    cam = vvec @ R
    z = cam[:, 2]
    infront = z > 1e-9
    zz = np.where(infront, z, 1.0)
    x, y = cam[:, 0] / zz, cam[:, 1] / zz
    r2 = x * x + y * y
    f = 1.0 + k1 * r2 + k2 * r2 * r2
    u = w / 2.0 + focal * x * f
    v = h / 2.0 - focal * y * f
    inside = infront & (u >= 0) & (u < w) & (v >= 0) & (v < h)
    return np.stack([u, v], -1), inside


def _bearings_dist(uv, focal, k1, k2, w, h):
    xd = (uv[:, 0] - w / 2.0) / focal
    yd = -(uv[:, 1] - h / 2.0) / focal
    x, y = xd.copy(), yd.copy()
    for _ in range(8):                       # invert r_d = r_u (1 + k1 r_u^2 + k2 r_u^4)
        r2 = x * x + y * y
        f = 1.0 + k1 * r2 + k2 * r2 * r2
        x, y = xd / f, yd / f
    return geometry.normalize(np.stack([x, y, np.ones_like(x)], -1))


def _verify_dist(R, focal, k1, k2, uv, vvec, w, h, pixel_tol):
    proj, vis = _project_dist(vvec, R, focal, k1, k2, w, h)
    pv = proj[vis]
    if len(pv) < 1:
        return 0, float("inf"), float("inf")
    d, _ = cKDTree(pv).query(uv, k=1)
    hit = d <= pixel_tol
    if not hit.any():
        return 0, float("inf"), float("inf")
    rpx = float(np.median(d[hit]))
    return int(hit.sum()), float(np.degrees(rpx / focal) * 3600.0), rpx


def _refine_dist(R, focal, k1, k2, uv, vvec, w, h, pixel_tol, iters=12):
    """Alternate R (Wahba on undistorted bearings) and a joint linear fit of focal + two
    radial-distortion terms (r_d_px = focal*r_u + focal*k1*r_u^3 + focal*k2*r_u^5). A
    loose->tight matching schedule grabs the distorted edge stars first (which pin down
    the distortion), then tightens -- turning a partial lock into a full one on a real
    wide-angle photo."""
    cx, cy = w / 2.0, h / 2.0
    tols = np.linspace(max(pixel_tol * 3.0, 7.0), pixel_tol, iters)
    for it in range(iters):
        proj, vis = _project_dist(vvec, R, focal, k1, k2, w, h)
        pv, vidx = proj[vis], np.where(vis)[0]
        if len(pv) < 5:
            break
        d, j = cKDTree(pv).query(uv, k=1)
        hit = d <= tols[it]
        if hit.sum() < 5:
            break
        uvh, catv = uv[hit], vvec[vidx[j[hit]]]
        R = _wahba(_bearings_dist(uvh, focal, k1, k2, w, h), catv)
        cam = catv @ R
        zc = cam[:, 2]
        ok = zc > 1e-6
        if ok.sum() >= 8:
            xu, yu = cam[ok, 0] / zc[ok], cam[ok, 1] / zc[ok]
            ru = np.sqrt(xu * xu + yu * yu)
            rd = np.sqrt((uvh[ok, 0] - cx) ** 2 + (uvh[ok, 1] - cy) ** 2)
            good = ru > 1e-3
            if good.sum() >= 8:
                A = np.stack([ru[good], ru[good] ** 3, ru[good] ** 5], axis=1)
                sol, *_ = np.linalg.lstsq(A, rd[good], rcond=None)
                if sol[0] > 1e-6:
                    focal = float(sol[0])
                    k1 = float(np.clip(sol[1] / sol[0], -1.0, 1.0))
                    k2 = float(np.clip(sol[2] / sol[0], -1.0, 1.0))
    n_in, resid_as, rpx = _verify_dist(R, focal, k1, k2, uv, vvec, w, h, pixel_tol)
    return R, focal, k1, k2, n_in, resid_as, rpx


def solve_one_dist(uv, flux, w, h, idx, code_tol=0.012, pixel_tol=2.5,
                   resid_arcsec_max=90.0, top=8):
    """Distortion-aware single-layer solve. Collects candidate quad matches, refines the
    most promising with a radial-distortion model, keeps the one with the most inliers at
    an honest (arcsec) residual -- so wrong-scale matches can't sneak through."""
    uv = np.asarray(uv, float)
    N = len(uv)
    if N < 4:
        return None
    cx, cy = w / 2.0, h / 2.0
    xy = np.column_stack([uv[:, 0] - cx, -(uv[:, 1] - cy)])
    tree = cKDTree(uv)
    neg = -np.asarray(flux, float)
    cands = []
    for four in canonical_quads_img(uv, neg, tree):
        qc = quad_code(xy[four])
        if qc is None:
            continue
        code, order = qc
        dd, jj = idx.code_tree.query(code, k=5, distance_upper_bound=code_tol)
        for dist, qj in zip(np.atleast_1d(dd), np.atleast_1d(jj)):
            if not np.isfinite(dist) or qj >= len(idx.quads):
                continue
            ip = uv[[four[o] for o in order]]
            cv = idx.bvec[idx.quads[qj]]
            cab = geometry.angsep(cv[0], cv[1])
            iab = float(np.linalg.norm(ip[0] - ip[1]))
            if cab < 1e-9 or iab < 1e-6:
                continue
            focal = iab / cab
            fov = geometry.fov_deg_from_focal(focal, w)
            if fov < 4.0 or fov > 130.0:
                continue
            R = _wahba(geometry.unproject(ip, np.eye(3), focal, w, h), cv)
            n0, _, _ = _verify_dist(R, focal, 0.0, 0.0, uv, idx.verify_vec, w, h, pixel_tol)
            cands.append((n0, R, focal))
    if not cands:
        return None
    cands.sort(key=lambda c: -c[0])
    best = None
    for n0, R, focal in cands[:top]:
        Rr, fr, k1, k2, n_in, resid_as, rpx = _refine_dist(
            R, focal, 0.0, 0.0, uv, idx.verify_vec, w, h, pixel_tol)
        if resid_as > resid_arcsec_max:
            continue
        if best is None or n_in > best["n_inliers"]:
            c = _bearings_dist(np.array([[cx, cy]]), fr, k1, k2, w, h)[0] @ Rr.T
            ra, dec = geometry.vec_to_radec(c)
            best = {"R": Rr, "focal": float(fr), "k1": float(k1), "n_inliers": int(n_in),
                    "n_used": N, "residual_arcsec": float(resid_as),
                    "fov_deg": float(geometry.fov_deg_from_focal(fr, w)),
                    "center_radec_deg": (float(np.degrees(ra)), float(np.degrees(dec)))}
    return best


def solve_dist(uv, flux, w, h, layers, K_list=(20, 35, 60, 100), min_inliers=14, **kw):
    uv, flux = np.asarray(uv, float), np.asarray(flux, float)
    best = None
    for layer in layers:
        for K in K_list:
            m = min(K, len(uv))
            if m < 8:
                continue
            r = solve_one_dist(uv[:m], flux[:m], w, h, layer, **kw)
            if r is None:
                continue
            r["layer_mag"] = layer.match_mag
            if best is None or r["n_inliers"] > best["n_inliers"]:
                best = r
            if r["n_inliers"] >= max(min_inliers, int(0.45 * m)):
                return best
    return best if (best and best["n_inliers"] >= min_inliers) else None


# --------------------------------------------------------------------------- #
# sensor-prior WARM-STARTED solve: blind -> local search around a predicted region
# --------------------------------------------------------------------------- #
_CAT = None


def _catalog(verify_mag=8.0):
    global _CAT
    from aerogaze.catalog import load_hyg
    if _CAT is None or _CAT[0] < verify_mag:
        _CAT = (verify_mag, load_hyg(mag_limit=verify_mag))
    return _CAT[1]


def predict_boresight(lat_deg, lon_deg, utc, alt_deg, az_deg):
    """Where (RA/Dec) does a camera at (lat,lon) pointed (alt,az) look, at time utc?
    A rough location prior + gravity(alt) + compass(az) + clock => a sky region to search."""
    from aerogaze import astro_lite
    jd = astro_lite.julian_date(utc)
    lst = np.radians((astro_lite.gmst_deg(jd) + lon_deg) % 360.0)
    a, A, phi = np.radians(alt_deg), np.radians(az_deg), np.radians(lat_deg)
    dec = np.arcsin(np.sin(a) * np.sin(phi) + np.cos(a) * np.cos(phi) * np.cos(A))
    H = np.arctan2(-np.sin(A) * np.cos(a),
                   np.cos(phi) * np.sin(a) - np.sin(phi) * np.cos(a) * np.cos(A))
    ra = (lst - H) % (2 * np.pi)
    return float(np.degrees(ra)), float(np.degrees(dec))


class _LocalLayer:
    def __init__(self, bvec, verify_vec, codes, quads):
        self.bvec, self.verify_vec = bvec, verify_vec
        self.codes, self.quads = codes, quads
        self.code_tree = cKDTree(codes)
        self.match_mag = 0.0


def solve_local(uv, flux, w, h, ra0_deg, dec0_deg, radius_deg=22.0,
                match_mag=6.5, verify_mag=8.0, K_list=(25, 50, 100), **kw):
    """Warm-started solve: restrict the catalog to a sky region around a predicted
    boresight (from the sensor + rough-location prior) and match there. A local search is
    far more robust than a global blind one and cracks fields that fail fully blind."""
    center = geometry.radec_to_vec(np.radians(ra0_deg), np.radians(dec0_deg))
    cat = _catalog(verify_mag)
    near = geometry.angsep(cat.vec, center) <= np.radians(radius_deg + 8.0)
    vvec = cat.vec[near].astype(np.float64)
    vmag = cat.mag[near]
    bmask = vmag <= match_mag
    bvec, bmag = vvec[bmask], vmag[bmask]
    if len(bvec) < 8:
        return None
    tree = cKDTree(bvec)
    codes, quads = [], []
    for four in canonical_quads(bvec, bmag, tree):
        pts = tangent_project(bvec[four], bvec[four].mean(0))
        qc = quad_code(pts)
        if qc is not None:
            codes.append(qc[0]); quads.append([four[o] for o in qc[1]])
    if not codes:
        return None
    layer = _LocalLayer(bvec, vvec, np.array(codes), np.array(quads, np.int32))
    best = None
    for K in K_list:
        m = min(K, len(uv))
        if m < 8:
            continue
        r = solve_one_dist(uv[:m], flux[:m], w, h, layer, **kw)
        if r is not None and (best is None or r["n_inliers"] > best["n_inliers"]):
            best = r
        if best is not None and best["n_inliers"] >= max(12, int(0.45 * m)):
            return best
    return best


def solve_prior(uv, flux, w, h, ra0, dec0, radius_deg=18.0,
                fov_grid=(45, 52, 60, 68, 76), roll_step=12, pos_step=6.0,
                match_tol=4.0, match_mag=7.0, verify_mag=8.5, min_match=9):
    """DIRECT attitude search around a sensor/location-derived prior boresight: try
    (RA, Dec, roll, FOV) on a grid, project the local catalog, count star coincidences,
    then refine the winner with distortion. Robust to lens distortion (we project with the
    model) -- this is what cracks wide real photos when a rough pointing prior is known."""
    uv = np.asarray(uv, float)
    if len(uv) < 6:
        return None
    center = geometry.radec_to_vec(np.radians(ra0), np.radians(dec0))
    cat = _catalog(verify_mag)
    near = geometry.angsep(cat.vec, center) <= np.radians(radius_deg + 14.0)
    locvec = cat.vec[near].astype(np.float64)
    locmag = cat.mag[near]
    mvec = locvec[locmag <= match_mag]                 # for the coincidence count
    if len(mvec) < 8:
        return None
    rolls = np.arange(0.0, 360.0, roll_step)
    ras = np.arange(ra0 - radius_deg, ra0 + radius_deg + 1e-3, pos_step)
    decs = np.arange(max(-89.0, dec0 - radius_deg), min(89.0, dec0 + radius_deg) + 1e-3, pos_step)
    cands = []                                          # (count, R, focal) grid candidates
    for fov in fov_grid:
        focal = geometry.focal_px_from_fov(fov, w)
        for ra in ras:
            for dec in decs:
                for roll in rolls:
                    R = geometry.rotation_from_boresight(np.radians(ra), np.radians(dec),
                                                         np.radians(roll))
                    proj, vis = geometry.project(mvec, R, focal, w, h)
                    pv = proj[vis]
                    if len(pv) < 6:
                        continue
                    dmin = np.sqrt(((uv[:, None, :] - pv[None, :, :]) ** 2).sum(-1).min(1))
                    cnt = int((dmin <= match_tol).sum())
                    if cnt >= min_match:
                        cands.append((cnt, R, focal))
    if not cands:
        return None
    # Refine the TOP-K grid candidates with distortion (the true attitude may not be the
    # single highest raw-count cell), and keep the one with the most real inliers.
    cands.sort(key=lambda c: -c[0])
    best = None
    for cnt, R, focal in cands[:10]:
        Rr, fr, k1, k2, n_in, resid_as, rpx = _refine_dist(R, focal, 0.0, 0.0, uv, locvec, w, h, match_tol)
        if best is None or n_in > best["n_inliers"]:
            c = _bearings_dist(np.array([[w / 2.0, h / 2.0]]), fr, k1, k2, w, h)[0] @ Rr.T
            ra, dec = geometry.vec_to_radec(c)
            best = {"R": Rr, "focal": float(fr), "k1": float(k1), "k2": float(k2),
                    "n_inliers": int(n_in), "n_used": int(len(uv)), "grid_matches": cnt,
                    "residual_arcsec": float(resid_as),
                    "fov_deg": float(geometry.fov_deg_from_focal(fr, w)),
                    "center_radec_deg": (float(np.degrees(ra)), float(np.degrees(dec)))}
    return best


def solve(uv, flux, w, h, layers, K_list=(15, 25, 40, 60, 90), min_inliers=12, **kw):
    """Density-matched multi-layer blind solve. `uv`/`flux` sorted brightest-first."""
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
            r["layer_mag"] = layer.match_mag
            r["K"] = m
            if best is None or r["n_inliers"] > best["n_inliers"]:
                best = r
            if r["n_inliers"] >= max(min_inliers, int(0.45 * m)):
                return best
    if best is not None and best["n_inliers"] >= min_inliers:
        return best
    return None
