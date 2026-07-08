"""Validate the pure-numpy astro_lite against astropy (the oracle).

For known (lat, lon, utc) we ask astropy for the ICRS direction of the local zenith,
feed it back through astro_lite.zenith_to_latlon, and require we recover the position.
This is what lets us trust the astronomy on-device, where astropy is unavailable.
"""
import numpy as np
import pytest

from aerogaze import astro_lite


astropy = pytest.importorskip("astropy")
import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers

# stay offline; tiny IERS extrapolation error (<< our budget) is fine
iers.conf.auto_download = False
iers.conf.iers_degraded_accuracy = "ignore"

CASES = [
    (38.99, -77.03, "2026-06-26T04:30:00"),   # Silver Spring, MD (BlairHacks)
    (0.0, 0.0, "2026-01-01T00:00:00"),
    (-33.87, 151.21, "2026-09-15T13:10:00"),  # Sydney
    (64.13, -21.90, "2026-12-21T23:45:00"),   # Reykjavik
    (-54.8, -68.3, "2026-03-20T06:00:00"),    # Ushuaia
]


def _astropy_zenith_icrs(lat, lon, utc):
    loc = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=0 * u.m)
    t = Time(utc, scale="utc")
    zen = SkyCoord(AltAz(alt=90 * u.deg, az=0 * u.deg, obstime=t, location=loc)).icrs
    c = zen.cartesian
    return np.array([c.x.value, c.y.value, c.z.value])


def _err_km(lat1, lon1, lat2, lon2):
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


@pytest.mark.parametrize("lat,lon,utc", CASES)
def test_recover_position(lat, lon, utc):
    zen = _astropy_zenith_icrs(lat, lon, utc)
    glat, glon = astro_lite.zenith_to_latlon(zen, utc)
    err = _err_km(lat, lon, glat, glon)
    assert err < 2.0, f"{utc}: {err:.3f} km (got {glat:.4f},{glon:.4f})"


def test_gmst_matches_astropy():
    for _, _, utc in CASES:
        t = Time(utc, scale="utc")
        ap = t.sidereal_time("mean", "greenwich").to_value(u.deg)
        ours = astro_lite.gmst_deg(astro_lite.julian_date(utc))
        diff = (ours - ap + 180) % 360 - 180
        assert abs(diff) < 0.01, f"GMST off by {diff*3600:.1f} arcsec at {utc}"


if __name__ == "__main__":
    for lat, lon, utc in CASES:
        zen = _astropy_zenith_icrs(lat, lon, utc)
        glat, glon = astro_lite.zenith_to_latlon(zen, utc)
        print(f"{utc}  truth=({lat:+.3f},{lon:+.3f})  ours=({glat:+.3f},{glon:+.3f})  "
              f"err={_err_km(lat, lon, glat, glon):.3f} km")
