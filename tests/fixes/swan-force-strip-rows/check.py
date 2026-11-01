"""Checks of 1-fixes/swan-force-strip-rows.patch (Inlet_test runs of run.sh).

    python -I check.py OUTDIR

OUTDIR/<side>-<n>swan/ (side before or after the patch, n = 1, 2, 3 SWAN
processes), each with SWAN's BLOCK output as .mat files.

Checks:
  bug        before: FORCE on 2 and 3 processes misses whole rows or columns
             that the 1-process run has
  fixed      after: FORCE on 2 and 3 processes equals the 1-process run, value
             for value, with nothing missing
  unchanged  every other .mat output, on every process count, and FORCE on 1
             process: before = after, bit for bit
  roms       the ROMS history (the coupled model): before = after, bit for bit
"""
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy.io import loadmat
from scipy.io.matlab import MatReadWarning

warnings.simplefilter("ignore", MatReadWarning)   # Inlet_test's botlev.mat repeats a name

out = Path(sys.argv[1])
ok = True


def verdict(name, good, text):
    global ok
    ok &= bool(good)
    print(f"{name:10s} {'PASS' if good else 'FAIL'}  {text}")


def mat(run, name):
    d = loadmat(run / name)
    return {k: np.asarray(v, float) for k, v in d.items()
            if not k.startswith("__") and np.asarray(v).dtype.kind in "fiu"}


def missing_lines(a, ref):
    """Rows and columns that are all NaN in a but not in ref (in any record)."""
    rows, cols = set(), set()
    for k in ref:
        x, r = a[k], ref[k]
        bad = np.isnan(x) & ~np.isnan(r)
        rows |= {i for i in range(x.shape[0]) if bad[i].all() or (bad[i].any() and np.isnan(x[i]).all())}
        cols |= {j for j in range(x.shape[1]) if bad[:, j].all() or (bad[:, j].any() and np.isnan(x[:, j]).all())}
    return sorted(rows), sorted(cols)


def same(a, b):
    return all(k in b and np.array_equal(a[k], b[k], equal_nan=True) for k in a) and set(a) == set(b)


for side in ("before", "after"):
    ref = mat(out / f"{side}-1swan", "force.mat")
    for n in (2, 3):
        f = mat(out / f"{side}-{n}swan", "force.mat")
        rows, cols = missing_lines(f, ref)
        nmiss = sum(int((np.isnan(f[k]) & ~np.isnan(ref[k])).sum()) for k in ref)
        both = {k: ~np.isnan(f[k]) & ~np.isnan(ref[k]) for k in ref}
        dmax = max(float(np.max(np.abs(f[k][both[k]] - ref[k][both[k]]), initial=0.0)) for k in ref)
        text = (f"{n} processes vs 1: {nmiss} values missing (rows {rows}, columns {cols}); "
                f"where both have values, max |diff| {dmax:.1e}")
        if side == "before":
            verdict("bug", nmiss > 0, text)
        else:
            verdict("fixed", nmiss == 0 and same(f, ref), text + ("; identical" if same(f, ref) else ""))

names = sorted(p.name for p in (out / "after-1swan").glob("*.mat"))
bad = []
for n in (1, 2, 3):
    for name in names:
        if name == "force.mat" and n > 1:
            continue
        if not same(mat(out / f"before-{n}swan", name), mat(out / f"after-{n}swan", name)):
            bad.append(f"{name} ({n})")
verdict("unchanged", not bad, f"{len(names)} .mat outputs x 3 process counts (FORCE on 1 only): "
        + ("all bit-identical before and after" if not bad else "differ: " + ", ".join(bad)))
from netCDF4 import Dataset


def his(run):
    return next(iter(sorted(run.glob("*his*.nc")) + sorted(run.glob("output/*his*.nc"))))


diff = []
for n in (1, 2, 3):
    with Dataset(his(out / f"before-{n}swan")) as a, Dataset(his(out / f"after-{n}swan")) as b:
        for v in a.variables:
            if v in b.variables and a[v].dtype.kind in "fiu" and not np.array_equal(
                    np.ma.filled(a[v][:], np.nan), np.ma.filled(b[v][:], np.nan), equal_nan=True):
                diff.append(f"{v} ({n})")
verdict("roms", not diff, "ROMS history, 1, 2, 3 SWAN processes: "
        + ("bit-identical before and after" if not diff else "differs: " + ", ".join(diff[:6])))
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
