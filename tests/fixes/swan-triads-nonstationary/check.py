"""Checks for tests/fixes/swan-triads-nonstationary (see run.sh).

    python -I check.py OUTDIR

OUTDIR holds the runs before/, after/ and after-notriad/ (output/ in each).
Prints each check with PASS or FAIL and the numbers; exit 1 on any FAIL.
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


def field(run, name):
    """SWAN BLOCK variable `name` (all output times), fill values as NaN."""
    d = Dataset(run / "output" / f"{name}.nc")
    v = [k for k in d.variables if d[k].ndim == 3][0]
    a = np.ma.filled(d[v][:].astype(float), np.nan)
    a[np.abs(a) >= 1e30] = np.nan
    return a


def same(fa, fb):
    """True if every variable of two NetCDF files is bit-identical."""
    a, b = Dataset(fa), Dataset(fb)
    for k in a.variables:
        if k in b.variables and not np.array_equal(np.ma.getdata(a[k][:]), np.ma.getdata(b[k][:])):
            return False, k
    return True, None


def main(out):
    out = Path(out)
    bad = 0
    tri_b, tri_a = field(out / "before", "redtriad"), field(out / "after", "redtriad")
    nb = int(np.nansum(np.abs(tri_b) > 0))
    ok = nb == 0
    print(f"bug       before: REDTRIAD nonzero at {nb} point-times (expected 0)"
          f"{'':10s}{'PASS' if ok else 'FAIL'}")
    bad += not ok
    na = int(np.nansum(np.abs(tri_a) > 0))
    hs_b, hs_a = field(out / "before", "hsign"), field(out / "after", "hsign")
    db = np.nanmax(np.abs(hs_a - hs_b))
    ok = na > 0 and db > 0
    print(f"fixed     after: REDTRIAD nonzero at {na} point-times, max |REDTRIAD| "
          f"{np.nanmax(np.abs(tri_a)):.3g}; Hs differs from before by up to {db:.3g} m"
          f"{'':4s}{'PASS' if ok else 'FAIL'}")
    bad += not ok
    files = sorted(p.name for p in (out / "before" / "output").glob("*.nc"))
    diff = []
    for f in files:
        ok_f, var = same(out / "before" / "output" / f, out / "after-notriad" / "output" / f)
        if not ok_f:
            diff.append(f"{f}:{var}")
    ok = not diff and files
    print(f"unchanged after-notriad vs before: {len(files)} output files "
          f"{'bit-identical' if not diff else 'differ: ' + ', '.join(diff[:5])}"
          f"{'':4s}{'PASS' if ok else 'FAIL'}")
    bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else __doc__)
