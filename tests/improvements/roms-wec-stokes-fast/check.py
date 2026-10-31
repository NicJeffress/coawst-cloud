"""Checks for 2-improvements/roms-wec-stokes-fast.patch.

    python -I check.py OUTDIR

OUTDIR/before and OUTDIR/after: Reef_Ideal_A15 runs (case_inside.sh) built
with PROFILE, without and with the patch. Checks:
  same physics  last history record: Stokes drift (u_stokes, v_stokes and
                their depth averages), currents, sea level, AKv, tke; the
                largest difference relative to the field's largest value
                must be below 1e-5 (the history is single precision, so
                rounding differences show as last-bit flips, about 1e-7)
  speed         CPU time of ROMS's "Waves Effect on Currents kernel" (the
                Stokes drift and the other wave terms), before and after;
                reported, and it must not grow
"""
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True
VARS = ("u_stokes", "v_stokes", "ubar_stokes", "vbar_stokes", "u", "v", "zeta", "AKv", "tke")


def check(name, good, text):
    global ok
    ok &= bool(good)
    print(f"{'ok ' if good else 'BAD'} {name}: {text}")


a = Dataset(out / "before" / "output" / "ocean_his.nc")
b = Dataset(out / "after" / "output" / "ocean_his.nc")
t = float(a["ocean_time"][-1]) / 60
worst = 0.0
for v in VARS:
    x = np.ma.filled(a[v][-1], np.nan).astype(float)
    y = np.ma.filled(b[v][-1], np.nan).astype(float)
    d, scale = np.abs(x - y), float(np.nanmax(np.abs(x)))
    rel = float(np.nanmax(d)) / scale if scale > 0 else 0.0
    worst = max(worst, rel)
    print(f"    {v:12s} max |diff| {np.nanmax(d):.2e} (largest value {scale:.3f}, relative {rel:.1e}); "
          f"{int(np.sum(d > 0))} of {d.size} points differ")
check("same physics", worst < 1e-5 and t == float(b["ocean_time"][-1]) / 60,
      f"at {t:.0f} min, largest relative difference {worst:.1e} (limit 1e-5)")


def wec_cpu(run):
    txt = (out / run / "log.txt").read_text(errors="replace")
    m = re.search(r"Waves Effect on Currents kernel \.+\s+([\d.]+)", txt)
    tot = re.search(r"Nonlinear model elapsed CPU time profile.*?Total:\s+([\d.]+)", txt, re.S)
    return (float(m.group(1)) if m else None), (float(tot.group(1)) if tot else None)


(wb, tb), (wa, ta) = wec_cpu("before"), wec_cpu("after")
if wb is None or wa is None:
    check("speed", False, "no PROFILE output (build with CPP_OPTIONS=+PROFILE)")
else:
    check("speed", wa <= wb, f"WEC kernel {wb:.0f} -> {wa:.0f} CPU-s summed over ROMS processes "
          f"({100 * (wa - wb) / wb:+.0f} %); ROMS profiled total {tb:.0f} -> {ta:.0f} CPU-s")
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
