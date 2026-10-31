"""Run checks for 1-fixes/roms-wetdry-stokes.patch.

    python -I check_runs.py OUTDIR

OUTDIR/wd-before, wd-after, nowd-after: Reef_Ideal_A15 runs (run.sh) with
WET_DRY before and after the patch, and without WET_DRY. Nothing dries in
this case, so with a correct WET_DRY the run should stay close to the one
without it. For each record, the largest difference from the run without
WET_DRY in the depth-averaged velocity (ubar, vbar) and sea level (zeta).
PASS if the difference before the patch is large (> 1 cm/s) and after it
small (< 1 mm/s) at the last record.
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ref = Dataset(out / "nowd-after/output/ocean_his.nc")
t = ref["ocean_time"][:] / 60.0
last = {}
for side in ("before", "after"):
    d = Dataset(out / f"wd-{side}/output/ocean_his.nc")
    n = min(len(d["ocean_time"]), len(t))
    rows = []
    for k in range(n):
        dif = {}
        for v in ("ubar", "vbar", "zeta"):
            a = np.ma.filled(d[v][k], np.nan).astype(float)
            b = np.ma.filled(ref[v][k], np.nan).astype(float)
            dif[v] = float(np.nanmax(np.abs(a - b)))
        rows.append(dif)
    print(f"WET_DRY {side} the patch vs no WET_DRY, largest |difference| per record:")
    for k, dif in enumerate(rows):
        print(f"   {t[k]:5.0f} min: ubar {dif['ubar']:.2e} m/s, vbar {dif['vbar']:.2e} m/s, zeta {dif['zeta']:.2e} m")
    last[side] = max(rows[-1]["ubar"], rows[-1]["vbar"])
vmax = float(np.nanmax(np.abs(np.ma.filled(ref["vbar"][-1], np.nan))))
print(f"largest |vbar| in the run without WET_DRY: {vmax:.2f} m/s")
ok = last["before"] > 1e-2 and last["after"] < 1e-3
print(f"before: {last['before']:.2e} m/s (> 1e-2: bug shown)   after: {last['after']:.2e} m/s (< 1e-3)   "
      + ("ok" if ok else "BAD"))
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
