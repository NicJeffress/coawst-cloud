"""Run checks for 1-fixes/roms-vegetation.patch on Reef_Ideal_A15_veg.

    python -I check_runs.py OUTDIR

OUTDIR holds the runs of run.sh (each with log.txt, image_info.txt, output/):
  before     the case, built without the patch
  after      the case, built with it
  zerogap    with the patch, plants 0.5 m thick (diameter x thickness x density = 1)
  nounits    with the patch except tau_veg_units (tau_veg from the work
             integrated over the cell, as in COAWST)
Checks (drag_work_array, zero_gap_stop) and the effect of tau_veg_units on
the canopy's eddy viscosity (AKv inside the 0.4 m canopy, last record).
Exit 0 if the checks pass.
"""
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True


def report(name, what, good, detail):
    global ok
    ok &= good
    print(f"{name:18s} {what:52s} {detail:40s} {'ok' if good else 'BAD'}")


def info(run):
    p = out / run / "image_info.txt"
    return p.read_text() if p.exists() else ""


def finished(run):
    m = re.search(r"exit (\d+)", info(run))
    return m is not None and m.group(1) == "0"


def log(run):
    p = out / run / "log.txt"
    return p.read_text(errors="replace") if p.exists() else ""


crash = re.search(r"(munmap_chunk|invalid pointer|free\(\)|Segmentation fault|corrupted|SIGSEGV|SIGABRT)",
                  log("before"))
report("drag_work_array", "before: ROMS crashes at the start",
       not finished("before") and crash is not None, crash.group(1) if crash else "no crash message")
report("drag_work_array", "after: the case runs to the end", finished("after"), info("after").strip().splitlines()[-1] if info("after") else "")
stop = "plants cover the whole bed" in log("zerogap")
report("zero_gap_stop", "plants covering the bed: stops with a message", stop and not finished("zerogap"),
       "message printed" if stop else "no message")
lines = log("zerogap").splitlines()
for k, line in enumerate(lines):
    if "VEGETATION_TURB - plants cover the whole bed" in line:
        for l in lines[k:k + 3]:
            print(f"                   | {l.strip()}")
        break

# tau_veg_units: effect on the canopy eddy viscosity
try:
    a, b = Dataset(out / "after/output/ocean_his.nc"), Dataset(out / "nounits/output/ocean_his.nc")
    akv_a, akv_b = np.ma.filled(a["AKv"][-1], np.nan), np.ma.filled(b["AKv"][-1], np.nan)
    h = a["h"][:]
    # height above the bed of the w levels (s-coordinate with zeta ~ 0 is enough here)
    hc = float(a["hc"][:]); sw = np.asarray(a["s_w"][:]); cw = np.asarray(a["Cs_w"][:])
    z = (hc * sw[:, None, None] + h[None] * cw[:, None, None]) * h[None] / (hc + h[None])
    above = z + h[None]
    canopy = (above > 0.01) & (above < 0.4)
    r = (akv_a / akv_b)[canopy]
    r = r[np.isfinite(r)]
    q = np.percentile(r, [10, 50, 90])
    print(f"{'tau_veg_units':18s} canopy AKv, patched / without units fix: 10/50/90 % = "
          f"{q[0]:.3f} / {q[1]:.3f} / {q[2]:.3f} ({r.size} points)")
except (FileNotFoundError, OSError, KeyError) as e:
    print(f"tau_veg_units      effect not computed ({e})")
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
