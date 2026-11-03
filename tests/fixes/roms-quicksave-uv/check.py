"""Checks for tests/fixes/roms-quicksave-uv (see run.sh).

    python -I check.py OUTDIR
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset


def main(out):
    out = Path(out)
    bad = 0
    q = {s: Dataset(out / s / "output" / "ocean_qck.nc") for s in ("before", "after")}
    h = {s: Dataset(out / s / "output" / "ocean_his.nc") for s in ("before", "after")}
    for s in q:
        q[s].set_auto_mask(False)
        h[s].set_auto_mask(False)
    # bug: before, u and v never written (fill values everywhere)
    fills = [np.all(np.abs(q["before"][v][:]) >= 1e30) for v in ("u", "v")]
    ok = all(fills)
    print(f"bug       before: quicksave u, v all fill values: {fills}{'':8s}{'PASS' if ok else 'FAIL'}")
    bad += not ok
    # fixed: after, equal to the history u, v at the common times
    tq, th = q["after"]["ocean_time"][:], h["after"]["ocean_time"][:]
    common = [t for t in tq if t in set(th)]
    worst = 0.0
    for t in common:
        iq, ih = int(np.where(tq == t)[0][0]), int(np.where(th == t)[0][0])
        for v in ("u", "v"):
            a, b = q["after"][v][iq], h["after"][v][ih]
            m = (np.abs(a) < 1e30) & (np.abs(b) < 1e30)
            worst = max(worst, float(np.max(np.abs(a[m] - b[m]))) if m.any() else np.inf)
    ok = len(common) > 1 and worst == 0.0
    print(f"fixed     after: quicksave u, v = history u, v at {len(common)} times, largest difference "
          f"{worst:.3g} m/s{'':4s}{'PASS' if ok else 'FAIL'}")
    bad += not ok
    # unchanged: history bit-identical before and after
    diff = [k for k in h["before"].variables
            if k in h["after"].variables and not np.array_equal(h["before"][k][:], h["after"][k][:])]
    ok = not diff
    print(f"unchanged history before vs after: {'bit-identical' if ok else 'differs in ' + ', '.join(diff[:5])}"
          f"{'':4s}{'PASS' if ok else 'FAIL'}")
    bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]) if len(sys.argv) == 2 else __doc__)
