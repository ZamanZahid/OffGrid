"""IMU fusion: combine the plate-solved attitude with the gravity vector to find
the celestial direction of the zenith.

The stars give the camera's orientation in the sky (``R_cam2sky``); they cannot tell
us which way is "down". The accelerometer's gravity vector supplies that one missing
reference. Composing them places the zenith on the celestial sphere -- and the
zenith's coordinates are exactly the observer's position (see astro_lite).
"""
from __future__ import annotations

import numpy as np

from . import geometry

# camera<->device extrinsic. On a phone the camera and IMU share a known fixed frame;
# identity is the right default for our synthetic captures and a good starting point
# for a real device (refine with a one-time calibration if needed).
R_DEVICE2CAM = np.eye(3)


def gravity_from_horizon(alt_deg, roll_deg=0.0):
    """Device gravity vector for a photo taken at a known camera elevation.

    For an uploaded photo there is no recorded accelerometer reading, so the user tells
    us the camera's altitude above the horizon (``alt_deg`` = 90 means pointed straight
    up at the zenith) and, optionally, the roll about the view axis (0 = phone upright).
    This returns the corresponding "down" vector in the camera frame.

    Referenced to the LOCAL VERTICAL -- what a phone's accelerometer actually senses --
    not the celestial pole, and reuses :func:`geometry.rotation_from_boresight` so the
    convention matches the solver exactly. The result depends only on altitude and roll,
    never on azimuth (which the stars already pin down), so the user need not face north.
    """
    a = np.radians(alt_deg)
    ra = np.pi / 2.0 - 0.0                    # azimuth is irrelevant; fix it at 0
    R = geometry.rotation_from_boresight(ra, a, np.radians(roll_deg))
    up_local = np.array([0.0, 0.0, 1.0])      # local zenith in the canonical frame
    return geometry.normalize(-(R.T @ up_local))   # gravity = -up, in the camera frame


def zenith_from_attitude(R_cam2sky, gravity_device, R_device2cam=None):
    """-> zenith unit vector in the sky (ICRS) frame.

    ``R_cam2sky`` from the plate solve, ``gravity_device`` from the accelerometer
    (any scale; only its direction matters).
    """
    if R_device2cam is None:
        R_device2cam = R_DEVICE2CAM
    up_device = -geometry.normalize(np.asarray(gravity_device, dtype=float))
    up_cam = R_device2cam @ up_device
    return geometry.normalize(R_cam2sky @ up_cam)
