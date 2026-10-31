"""Run checks for 1-fixes/roms-restart-wec.patch.

    python -I check_runs.py OUTDIR

OUTDIR/<variant>-<side>/{straight,part1,part2} from run.sh (restart_inside.sh),
variant = veg (Reef_Ideal_A15_veg) or river (Reef_Ideal_A15 with a river),
side = before or after the patch. For each, compares the last record of the
restarted run (part2) with the uninterrupted one (straight): ROMS history
(ubar, vbar, u, v, zeta, AKv, tke) and SWAN's Hs.
Also OUTDIR/noriver-after: Reef_Ideal_A15 without the river, after the patch:
the baseline of the river variant (base A15 restarts to about 1e-7 m/s, a
small residual that has nothing to do with rivers; see the patch document).
PASS if the restarted run differs before the patch by more than 1e-6 m/s, and
after it by less than 1e-8 m/s (veg, round-off) or by no more than 3 times
the no-river baseline (river).
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True
baseline = None
ROMS = ("ubar", "vbar", "u", "v", "zeta", "AKv", "tke")


def last_diff(a, b, var):
    if var not in a.variables or var not in b.variables:
        return None
    x = np.ma.filled(a[var][-1], np.nan).astype(float)
    y = np.ma.filled(b[var][-1], np.nan).astype(float)
    return float(np.nanmax(np.abs(x - y)))


for variant in ("noriver", "veg", "river"):
    res = {}
    for side in (("after",) if variant == "noriver" else ("before", "after")):
        base = out / f"{variant}-{side}"
        try:
            s = Dataset(base / "straight/output/ocean_his.nc")
            p = Dataset(base / "part2/output/ocean_his.nc")
        except (FileNotFoundError, OSError) as e:
            print(f"{variant:5s} {side:6s}: missing output ({e})")
            ok = False
            continue
        t_s, t_p = float(s["ocean_time"][-1]) / 60, float(p["ocean_time"][-1]) / 60
        d = {v: last_diff(s, p, v) for v in ROMS}
        hs = None
        try:
            hs = last_diff(Dataset(base / "straight/output/hsign.nc"), Dataset(base / "part2/output/hsign.nc"), "hs")
        except (FileNotFoundError, OSError):
            pass
        vel = max(d[v] for v in ("ubar", "vbar", "u", "v") if d[v] is not None)
        res[side] = vel
        parts = ", ".join(f"{v} {d[v]:.1e}" for v in ROMS if d[v] is not None)
        print(f"{variant:5s} {side:6s} at {t_s:.0f}/{t_p:.0f} min: currents {vel:.1e} m/s; {parts}"
              + (f"; SWAN Hs {hs:.1e} m" if hs is not None else ""))
    if variant == "noriver":
        baseline = res.get("after")
        continue
    if variant == "veg":
        good = res.get("before", 0) > 1e-6 and res.get("after", 1) < 1e-8
    else:
        good = res.get("before", 0) > 1e-6 and res.get("after", 1) <= 3 * max(baseline or 0, 1e-8)
    ok &= good
    print(f"{variant:5s} restarted vs straight: before {res.get('before', float('nan')):.1e}, "
          f"after {res.get('after', float('nan')):.1e} m/s  {'ok' if good else 'BAD'}")
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
