"""Shared geometry: unit vectors, rotations, and the gnomonic camera model.

Conventions
-----------
* Celestial frame is ICRS (J2000). A direction is a 3-vector
  ``[cos(dec) cos(ra), cos(dec) sin(ra), sin(dec)]`` (a unit vector on the sphere).
* The camera looks along its local **+Z** axis (the boresight). Image axes are
  **+X right, +Y up** in the camera frame; pixel **v** increases downward, so the
  projection flips Y (standard image convention).
* ``R_cam2sky`` is a 3x3 rotation whose columns are the camera axes expressed in the
  sky frame, so ``sky_vec = R_cam2sky @ cam_vec`` and ``cam_vec = R_cam2sky.T @ sky_vec``.

All angles are radians unless a name ends in ``_deg``. numpy only (Chaquopy-safe).
"""
from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------------- #
# unit vectors <-> spherical coordinates
# --------------------------------------------------------------------------- #
def radec_to_vec(ra, dec):
    """(ra, dec) in radians -> unit vector(s). Accepts scalars or arrays."""
    ra = np.asarray(ra, dtype=float)
    dec = np.asarray(dec, dtype=float)
    cd = np.cos(dec)
    return np.stack([cd * np.cos(ra), cd * np.sin(ra), np.sin(dec)], axis=-1)


def vec_to_radec(v):
    """Unit vector(s) -> (ra, dec) in radians. ra is wrapped to [0, 2pi)."""
    v = np.asarray(v, dtype=float)
    x, y, z = v[..., 0], v[..., 1], v[..., 2]
    ra = np.mod(np.arctan2(y, x), 2.0 * np.pi)
    dec = np.arctan2(z, np.hypot(x, y))
    return ra, dec


def normalize(v, axis=-1):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.where(n == 0.0, 1.0, n)


def angsep(v1, v2):
    """Angular separation (radians) between two unit vectors (broadcasts)."""
    v1 = normalize(v1)
    v2 = normalize(v2)
    dot = np.clip(np.sum(v1 * v2, axis=-1), -1.0, 1.0)
    return np.arccos(dot)


# --------------------------------------------------------------------------- #
# rotations
# --------------------------------------------------------------------------- #
def rotation_from_boresight(ra, dec, roll=0.0):
    """Build ``R_cam2sky`` for a camera pointed at (ra, dec) with a roll angle.

    roll=0 puts celestial "up" (toward +Dec / the north celestial pole) along the
    camera +Y axis. Positive roll rotates the camera clockwise about its boresight.
    """
    z = radec_to_vec(ra, dec)                      # boresight, in sky frame
    # north celestial pole direction; degenerate only when looking straight at a pole
    pole = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(z, pole))) > 0.999999:
        pole = np.array([1.0, 0.0, 0.0])
    x = normalize(np.cross(pole, z))               # camera +X (sky frame)
    y = np.cross(z, x)                             # camera +Y (sky frame)
    R = np.stack([x, y, z], axis=1)               # columns = cam axes in sky frame
    if roll:
        c, s = np.cos(roll), np.sin(roll)
        Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        R = R @ Rz
    return R


def quat_to_matrix(q):
    """Quaternion [w, x, y, z] -> 3x3 rotation matrix."""
    w, x, y, z = q
    n = np.sqrt(w * w + x * x + y * y + z * z)
    if n == 0:
        return np.eye(3)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


# --------------------------------------------------------------------------- #
# camera intrinsics + gnomonic (TAN) projection
# --------------------------------------------------------------------------- #
def focal_px_from_fov(fov_deg, width_px):
    """Pixels of focal length from a horizontal field of view."""
    return (width_px / 2.0) / np.tan(np.radians(fov_deg) / 2.0)


def fov_deg_from_focal(focal_px, width_px):
    return np.degrees(2.0 * np.arctan((width_px / 2.0) / focal_px))


def project(sky_vecs, R_cam2sky, focal_px, width, height):
    """Project sky unit vectors to pixel coordinates.

    Returns (uv, visible) where ``uv`` is (N, 2) of (col, row) pixels and ``visible``
    is a bool mask of stars in front of the camera and inside the frame.
    """
    sky_vecs = np.asarray(sky_vecs, dtype=float)
    cam = sky_vecs @ R_cam2sky                      # sky -> cam  (== R.T @ v per row)
    cx, cy = width / 2.0, height / 2.0
    vz = cam[:, 2]
    in_front = vz > 1e-9
    safe_vz = np.where(in_front, vz, 1.0)
    u = cx + focal_px * (cam[:, 0] / safe_vz)
    v = cy - focal_px * (cam[:, 1] / safe_vz)       # flip Y for image row convention
    uv = np.stack([u, v], axis=-1)
    inside = (u >= 0) & (u < width) & (v >= 0) & (v < height)
    return uv, in_front & inside


def unproject(uv, R_cam2sky, focal_px, width, height):
    """Inverse of :func:`project`: pixel coordinates -> sky unit vectors."""
    uv = np.asarray(uv, dtype=float)
    cx, cy = width / 2.0, height / 2.0
    x = (uv[..., 0] - cx) / focal_px
    y = -(uv[..., 1] - cy) / focal_px
    cam = np.stack([x, y, np.ones_like(x)], axis=-1)
    cam = normalize(cam)
    return cam @ R_cam2sky.T                         # cam -> sky
