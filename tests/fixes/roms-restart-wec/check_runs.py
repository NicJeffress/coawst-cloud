"""Run checks for 1-fixes/roms-restart-wec.patch.

    python -I check_runs.py OUTDIR

OUTDIR/<variant>-<side>/{straight,part1,part2} from run.sh (restart_inside.sh),
variant = veg (Reef_Ideal_A15_veg), river (Reef_Ideal_A15 with a river) or
noriver (the same image with the river off: base A15, periodic in x, GLS),
side = before or after the patch. For each, compares the last record of the
restarted run (part2) with the uninterrupted one (straight): ROMS history
(ubar, vbar, u, v, zeta, AKv, tke) and SWAN's Hs.
PASS if the restarted run differs before the patch by more than 1e-6 m/s, and
after it by less than 1e-8 m/s (round-off: the history is written in single
precision, so what is left are flips of the last bit, 2e-9 m/s at 0.03 m/s).
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True
ROMS = ("ubar", "vbar", "u", "v", "zeta", "AKv", "tke")


def last_diff(a, b, var):
    if var not in a.variables or var not in b.variables:
        return None
    x = np.ma.filled(a[var][-1], np.nan).astype(float)
    y = np.ma.filled(b[var][-1], np.nan).astype(float)
    return float(np.nanmax(np.abs(x - y)))


for variant in ("veg", "river", "noriver"):
    res = {}
    for side in ("before", "after"):
        base = out / f"{variant}-{side}"
        try:
            s = Dataset(base / "straight/output/ocean_his.nc")
            p = Dataset(base / "part2/output/ocean_his.nc")
        except (FileNotFoundError, OSError) as e:
            print(f"{variant:7s} {side:6s}: missing output ({e})")
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
        print(f"{variant:7s} {side:6s} at {t_s:.0f}/{t_p:.0f} min: currents {vel:.1e} m/s; {parts}"
              + (f"; SWAN Hs {hs:.1e} m" if hs is not None else ""))
    good = res.get("before", 0) > 1e-6 and res.get("after", 1) < 1e-8
    ok &= good
    print(f"{variant:7s} restarted vs straight: before {res.get('before', float('nan')):.1e}, "
          f"after {res.get('after', float('nan')):.1e} m/s  {'ok' if good else 'BAD'}")
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
