"""Checks for 1-fixes/roms-ts-fixed-density.patch (see run.sh).

    python -I check.py OUTDIR

OUTDIR/tsfixed-<side>/{straight,part2}/output/ocean_rst.nc: the restart record at the
end of the run (double precision), side = before or after the patch. The restarted run
(part2) must equal the uninterrupted one (straight) to the last bit in u, v, ubar, vbar
and zeta after the patch, and differ before it. OUTDIR/evolve-<side>: 10 min without
TS_FIXED; their histories must be identical.
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
STATE = ("u", "v", "ubar", "vbar", "zeta")


def compare(side):
    d = out / f"tsfixed-{side}"
    with Dataset(d / "straight/output/ocean_rst.nc") as a, Dataset(d / "part2/output/ocean_rst.nc") as b:
        ta, tb = list(np.asarray(a["ocean_time"][:])), list(np.asarray(b["ocean_time"][:]))
        t = max(set(ta) & set(tb))
        ia, ib = ta.index(t), tb.index(t)
        res = {}
        for v in STATE:
            x = np.ma.filled(a[v][ia], 0.0).astype(float) + 0.0     # +0.0: -0 and +0 alike
            y = np.ma.filled(b[v][ib], 0.0).astype(float) + 0.0
            res[v] = (float(np.abs(x - y).max()), int((x != y).sum()))
    print(f"   tsfixed-{side} at {t / 60:.0f} min: " + ", ".join(f"{v} {m:.1e} ({n} points)" for v, (m, n) in res.items()))
    return res


ok = True
res = {}
for side in ("before", "after"):
    try:
        res[side] = compare(side)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"   tsfixed-{side}: missing output ({exc!r})")
good = "before" in res and any(n > 0 for _, n in res["before"].values())
ok &= good
print(f"   bug       before: restarted run differs    {'PASS' if good else 'FAIL'}")
good = "after" in res and all(n == 0 for _, n in res["after"].values())
ok &= good
print(f"   fixed     after: restarted run bit-identical    {'PASS' if good else 'FAIL'}")
try:
    with Dataset(out / "evolve-before/output/ocean_his.nc") as a, Dataset(out / "evolve-after/output/ocean_his.nc") as b:
        good = len(a["ocean_time"]) > 1 and all(
            np.array_equal(np.ma.filled(a[v][:], 0), np.ma.filled(b[v][:], 0))
            for v in a.variables if a[v].dimensions[:1] == ("ocean_time",))
except (FileNotFoundError, OSError):
    good = False
ok &= good
print(f"   unchanged runs without TS_FIXED: {'bit-identical' if good else 'different or missing'}    "
      f"{'PASS' if good else 'FAIL'}")
sys.exit(0 if ok else 1)
