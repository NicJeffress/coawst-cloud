"""Compare two NetCDF files variable by variable.

    python -I tests/tools/compare_nc.py FILE_A FILE_B [VAR ...] [--last]

For every variable present in both files (or the ones named), prints the
largest absolute difference, where it is (index of the first largest), the
largest absolute value in FILE_A, and whether the two are bit-identical.
Fill values (|x| >= 1e30, e.g. land points) are left out of the maximums.
--last compares only the last record of variables with a time dimension.
Exit status 0 if every compared variable is bit-identical, 1 otherwise.
Needs numpy and netCDF4.
"""
import sys

import numpy as np
from netCDF4 import Dataset


def main(argv):
    last = "--last" in argv
    args = [a for a in argv if a != "--last"]
    if len(args) < 2:
        sys.exit(__doc__)
    fa, fb, names = args[0], args[1], args[2:]
    a, b = Dataset(fa), Dataset(fb)
    for d in (a, b):
        d.set_auto_mask(False)
    names = names or [v for v in a.variables if v in b.variables]
    same_all = True
    print(f"{'variable':24s} {'max |A-B|':>12s} {'max |A|':>12s}  at (index)       identical")
    for n in names:
        if n not in a.variables or n not in b.variables:
            print(f"{n:24s} (not in both files, skipped)")
            continue
        va, vb = a.variables[n], b.variables[n]
        if va.shape != vb.shape:
            print(f"{n:24s} shapes differ {va.shape} {vb.shape}")
            same_all = False
            continue
        timed = last and va.dimensions and "time" in va.dimensions[0]
        xa = va[-1] if timed else va[:]
        xb = vb[-1] if timed else vb[:]
        if xa.dtype.kind not in "fiu":
            continue
        xa, xb = np.asarray(xa, float), np.asarray(xb, float)
        same = np.array_equal(xa, xb, equal_nan=True)
        same_all &= same
        fill = (np.abs(xa) >= 1e30) | (np.abs(xb) >= 1e30)  # land / fill values
        xa[fill] = np.nan
        xb[fill] = np.nan
        d = np.abs(xa - xb)
        d[np.isnan(d)] = 0.0
        dmax = float(d.max()) if d.size else 0.0
        where = np.unravel_index(int(d.argmax()), d.shape) if d.size and dmax > 0 else ()
        amax = float(np.nanmax(np.abs(xa))) if xa.size else 0.0
        print(f"{n:24s} {dmax:12.4g} {amax:12.4g}  {str(tuple(int(i) for i in where)):16s} {'yes' if same else 'NO'}")
    print("ALL BIT-IDENTICAL" if same_all else "DIFFERENCES FOUND")
    return 0 if same_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
