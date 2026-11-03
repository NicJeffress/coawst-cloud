"""Checks for 1-fixes/roms-restart-roller.patch.

    python -I check.py OUTDIR

OUTDIR/roller-<side>/{straight,part1,part2} from run.sh (restart_inside.sh),
side = before or after the patch; OUTDIR/plain-<side> 10 min without
ROLLER_RENIERS. Compares the last record of the
restarted run (part2) with the uninterrupted one (straight): ROMS history
(ubar, vbar, u, v, zeta, AKv) and SWAN's Hs.
PASS if before the patch the currents differ by more than 1e-6 m/s, after it
by less than 1e-8 m/s (the history is single precision: what is left are flips
of the last bit), and the runs without the roller are bit-identical.
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True
ROMS = ("ubar", "vbar", "u", "v", "zeta", "AKv")


def last_diff(a, b, var):
    if var not in a.variables or var not in b.variables:
        return None
    x = np.ma.filled(a[var][-1], np.nan).astype(float)
    y = np.ma.filled(b[var][-1], np.nan).astype(float)
    return float(np.nanmax(np.abs(x - y)))


res = {}
for side in ("before", "after"):
    base = out / f"roller-{side}"
    try:
        s = Dataset(base / "straight/output/ocean_his.nc")
        p = Dataset(base / "part2/output/ocean_his.nc")
    except (FileNotFoundError, OSError) as e:
        print(f"   roller-{side}: missing output ({e})")
        ok = False
        continue
    t_s, t_p = float(s["ocean_time"][-1]) / 60, float(p["ocean_time"][-1]) / 60
    d = {v: last_diff(s, p, v) for v in ROMS}
    hs = None
    try:
        hs = last_diff(Dataset(base / "straight/output/hsign.nc"), Dataset(base / "part2/output/hsign.nc"), "hs")
    except (FileNotFoundError, OSError):
        pass
    res[side] = max(d[v] for v in ("ubar", "vbar", "u", "v") if d[v] is not None)
    parts = ", ".join(f"{v} {d[v]:.1e}" for v in ROMS if d[v] is not None)
    print(f"   roller-{side} at {t_s:.0f}/{t_p:.0f} min: currents {res[side]:.1e} m/s; {parts}"
          + (f"; SWAN Hs {hs:.1e} m" if hs is not None else ""))

good = res.get("before", 0) > 1e-6
ok &= good
print(f"   bug       before: restarted run {res.get('before', float('nan')):.1e} m/s off    {'PASS' if good else 'FAIL'}")
good = res.get("after", 1) < 1e-8
ok &= good
print(f"   fixed     after: restarted run {res.get('after', float('nan')):.1e} m/s off    {'PASS' if good else 'FAIL'}")
try:
    with Dataset(out / "plain-before/output/ocean_his.nc") as a, Dataset(out / "plain-after/output/ocean_his.nc") as b:
        good = len(a["ocean_time"]) > 1 and all(
            np.array_equal(np.ma.filled(a[v][:], 0), np.ma.filled(b[v][:], 0))
            for v in a.variables if a[v].dimensions[:1] == ("ocean_time",))
except (FileNotFoundError, OSError):
    good = False
ok &= good
print(f"   unchanged runs without ROLLER_RENIERS: {'bit-identical' if good else 'different or missing'}    "
      f"{'PASS' if good else 'FAIL'}")
sys.exit(0 if ok else 1)
