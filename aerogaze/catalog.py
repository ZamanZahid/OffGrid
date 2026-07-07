"""Load the HYG v4.1 star catalog into magnitude-filtered ICRS unit vectors.

Only used on the laptop (synthetic rendering + index building). On the phone we ship
the prebuilt index, not the raw CSV. Uses the stdlib ``csv`` module to avoid a pandas
dependency.

HYG column indices used: 0=id, 6=proper(name), 13=mag, 23=rarad, 24=decrad.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass

import numpy as np

from . import geometry

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "hygdata_v41.csv")

# column positions in the HYG v4.1 header
_COL_ID = 0
_COL_PROPER = 6
_COL_MAG = 13
_COL_RARAD = 23
_COL_DECRAD = 24


@dataclass
class Catalog:
    """A filtered star catalog as parallel arrays (sorted bright -> faint)."""
    ids: np.ndarray          # (N,) int   HYG id
    ra: np.ndarray           # (N,) float radians
    dec: np.ndarray          # (N,) float radians
    mag: np.ndarray          # (N,) float visual magnitude
    vec: np.ndarray          # (N, 3) float ICRS unit vectors
    names: list              # (N,) proper names ("" if none)

    def __len__(self):
        return len(self.ids)

    def brightest(self, n):
        """Return a new Catalog with only the n brightest stars."""
        n = min(n, len(self))
        return self._take(np.arange(n))

    def _take(self, idx):
        return Catalog(
            ids=self.ids[idx], ra=self.ra[idx], dec=self.dec[idx],
            mag=self.mag[idx], vec=self.vec[idx],
            names=[self.names[i] for i in idx],
        )


def load_hyg(path=None, mag_limit=6.5):
    """Load and filter the catalog.

    Parameters
    ----------
    path : str, optional
        Path to ``hygdata_v41.csv`` (defaults to the bundled copy in ``data/``).
    mag_limit : float
        Keep stars with visual magnitude <= this. ~6.5 ≈ naked-eye limit; raise it
        (e.g. 8) to model long-exposure phone captures that reach fainter stars.

    Returns a :class:`Catalog` sorted brightest-first, excluding the Sun (id 0).
    """
    if path is None:
        path = _DEFAULT_PATH
    ids, ra, dec, mag, names = [], [], [], [], []
    with open(path, "r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)  # header
        for row in reader:
            try:
                sid = int(row[_COL_ID])
                if sid == 0:                       # the Sun — not a navigation star
                    continue
                m = float(row[_COL_MAG])
            except (ValueError, IndexError):
                continue
            if m > mag_limit:
                continue
            ids.append(sid)
            ra.append(float(row[_COL_RARAD]))
            dec.append(float(row[_COL_DECRAD]))
            mag.append(m)
            names.append(row[_COL_PROPER])

    ids = np.asarray(ids, dtype=np.int64)
    ra = np.asarray(ra, dtype=float)
    dec = np.asarray(dec, dtype=float)
    mag = np.asarray(mag, dtype=float)

    order = np.argsort(mag)                          # brightest first
    ids, ra, dec, mag = ids[order], ra[order], dec[order], mag[order]
    names = [names[i] for i in order]
    vec = geometry.radec_to_vec(ra, dec)
    return Catalog(ids=ids, ra=ra, dec=dec, mag=mag, vec=vec, names=names)


if __name__ == "__main__":
    cat = load_hyg()
    print(f"Loaded {len(cat)} stars (mag <= 6.5).")
    print("Brightest 5:")
    for i in range(5):
        nm = cat.names[i] or "(unnamed)"
        print(f"  {nm:12s} mag={cat.mag[i]:+.2f} "
              f"ra={np.degrees(cat.ra[i]):7.2f} dec={np.degrees(cat.dec[i]):+6.2f}")
