"""Pure-numpy positional astronomy: zenith direction + UTC -> latitude/longitude.

No astropy here so this runs unchanged on-device under Chaquopy. The values are
validated against astropy on the laptop (see tests/test_astro_lite.py).

Core relationship (the whole project)::

    latitude  = Dec of the zenith (in the equator-of-date frame)
    longitude = RA_zenith - GMST(UTC)        # east-positive, normalized to +-180 deg

We precess the ICRS/J2000 zenith vector to the mean equator/equinox of date before
reading off RA/Dec, because over ~26 years since J2000 precession is ~0.36 deg
(~40 km) -- far larger than our error budget. Nutation and the equation of the
equinoxes (~arcsec) are neglected.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from . import geometry

ARCSEC = np.pi / (180.0 * 3600.0)


# --------------------------------------------------------------------------- #
# time
# --------------------------------------------------------------------------- #
def parse_utc(ts):
    """Parse an ISO-8601 UTC timestamp (or pass through a datetime) -> aware UTC."""
    if isinstance(ts, datetime):
        dt = ts
    else:
        s = str(ts).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def julian_date(ts):
    """Julian Date (UTC) from an ISO timestamp or datetime."""
    dt = parse_utc(ts)
    y, m = dt.year, dt.month
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    day_frac = (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6) / 60.0) / 60.0) / 24.0
    jd0 = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + dt.day + b - 1524.5
    return jd0 + day_frac


def gmst_deg(jd):
    """Greenwich Mean Sidereal Time in degrees [0, 360) from Julian Date (UTC)."""
    d = jd - 2451545.0
    t = d / 36525.0
    gmst = (280.46061837 + 360.98564736629 * d
            + 0.000387933 * t * t - t * t * t / 38710000.0)
    return gmst % 360.0


# --------------------------------------------------------------------------- #
# precession (IAU 1976, Lieske) : J2000 -> mean equinox of date
# --------------------------------------------------------------------------- #
def _R3(phi):
    c, s = np.cos(phi), np.sin(phi)
    return np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])


def _R2(phi):
    c, s = np.cos(phi), np.sin(phi)
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])


def precession_matrix(jd):
    """Matrix P with ``vec_date = P @ vec_J2000`` (mean equator/equinox of date)."""
    t = (jd - 2451545.0) / 36525.0
    zeta = (2306.2181 * t + 0.30188 * t * t + 0.017998 * t ** 3) * ARCSEC
    z = (2306.2181 * t + 1.09468 * t * t + 0.018203 * t ** 3) * ARCSEC
    theta = (2004.3109 * t - 0.42665 * t * t - 0.041833 * t ** 3) * ARCSEC
    return _R3(-z) @ _R2(theta) @ _R3(-zeta)


# --------------------------------------------------------------------------- #
# the payoff
# --------------------------------------------------------------------------- #
def zenith_to_latlon(zenith_icrs, utc):
    """ICRS zenith unit vector + UTC -> (lat_deg, lon_deg), lon east-positive."""
    jd = julian_date(utc)
    zen_date = precession_matrix(jd) @ geometry.normalize(np.asarray(zenith_icrs, float))
    ra, dec = geometry.vec_to_radec(zen_date)
    lat = np.degrees(dec)
    lst = np.degrees(ra)                     # local sidereal time = RA on the meridian
    lon = (lst - gmst_deg(jd) + 180.0) % 360.0 - 180.0
    return float(lat), float(lon)


def latlon_to_zenith_icrs(lat_deg, lon_deg, utc):
    """Inverse helper (used by the synthetic generator): where does the zenith point?"""
    jd = julian_date(utc)
    lst = (gmst_deg(jd) + lon_deg) % 360.0
    zen_date = geometry.radec_to_vec(np.radians(lst), np.radians(lat_deg))
    # date -> J2000 is the transpose of the precession matrix
    return precession_matrix(jd).T @ zen_date
