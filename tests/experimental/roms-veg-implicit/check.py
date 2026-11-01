"""Checks of 3-experimental/roms-veg-implicit.patch (runs of run.sh).

    python -I check.py OUTDIR

Reports for each run whether it finished (and when it stopped if not), and
compares at the last common record (depth-mean currents ubar/vbar at rho
points, sea level, Hs): implicit DT 6 s and DT 3 s against the explicit DT
3 s reference (patchy canopy), and implicit against explicit at DT 6 s
(uniform canopy): largest difference, the 99.9th percentile, RMS difference
relative to the RMS speed, and cells more than 1 cm/s apart.
PASS if every implicit run finished and the patchy implicit DT 6 s run is
within TOL m/s of the reference at 99.9 % of the cells.
"""
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
TOL = 0.02
ok = True


def status(run):
    info = (run / "image_info.txt").read_text() if (run / "image_info.txt").exists() else ""
    log = (run / "log.txt").read_text(errors="replace") if (run / "log.txt").exists() else ""
    wall = re.search(r"wall_s (\d+)", info)
    blow = re.search(r"Blowing-up: Saving latest model state into  RESTART file", log)
    t = None
    if (run / "output/ocean_his.nc").exists():
        with Dataset(run / "output/ocean_his.nc") as d:
            t = float(d["ocean_time"][-1]) / 60 if len(d["ocean_time"]) else None
    return ("exit 0" in info and not blow), (int(wall.group(1)) if wall else None), t, bool(blow)


def fields(run, t):
    with Dataset(run / "output/ocean_his.nc") as d:
        k = list(d["ocean_time"][:]).index(t)
        m = d["mask_rho"][:] > 0
        ub = np.ma.filled(d["ubar"][k].astype(float), np.nan)
        vb = np.ma.filled(d["vbar"][k].astype(float), np.nan)
        u = np.full(m.shape, np.nan)
        v = np.full(m.shape, np.nan)
        u[:, 1:-1] = 0.5 * (ub[:, :-1] + ub[:, 1:])
        v[1:-1] = 0.5 * (vb[:-1] + vb[1:])
        f = {"u": u, "v": v,
             "zeta": np.ma.filled(d["zeta"][k].astype(float), np.nan),
             "Hwave": np.ma.filled(d["Hwave"][k].astype(float), np.nan)}
        return {n: np.where(m, a, np.nan)[1:-1, 1:-1] for n, a in f.items()}


def compare(a, b, label):
    ra, rb = out / a, out / b
    with Dataset(ra / "output/ocean_his.nc") as x, Dataset(rb / "output/ocean_his.nc") as y:
        t = sorted(set(x["ocean_time"][:]) & set(y["ocean_time"][:]))[-1]
    fa, fb = fields(ra, t), fields(rb, t)
    du = np.hypot(fa["u"] - fb["u"], fa["v"] - fb["v"])
    du = du[np.isfinite(du)]
    sp = np.hypot(fb["u"], fb["v"])
    sp = sp[np.isfinite(sp)]
    dz = np.nanmax(np.abs(fa["zeta"] - fb["zeta"]))
    dh = np.nanmax(np.abs(fa["Hwave"] - fb["Hwave"]))
    p999 = float(np.percentile(du, 99.9))
    print(f"   {label} at {t / 60:.0f} min: current difference largest {du.max():.3f} m/s, 99.9 % of cells "
          f"within {p999:.4f} m/s, {int((du > 0.01).sum())} of {du.size} cells > 1 cm/s, RMS diff / RMS speed "
          f"{np.sqrt(np.mean(du ** 2)) / np.sqrt(np.mean(sp ** 2)):.3f}; sea level {dz:.1e} m; Hs {dh:.3f} m")
    return p999


runs = ["patchy-exp-dt6", "patchy-imp-dt6", "patchy-exp-dt3", "patchy-imp-dt3", "const-exp-dt6", "const-imp-dt6"]
st = {r: status(out / r) for r in runs}
print("== runs")
for r in runs:
    fin, wall, t, blow = st[r]
    print(f"   {r:16s} {'finished' if fin else ('BLEW UP' if blow else 'stopped')}"
          f"{'' if fin else f' (last output {t:.0f} min)' if t is not None else ''}, wall {wall} s")
good = all(st[r][0] for r in runs if "-imp-" in r) and st["patchy-exp-dt3"][0] and st["const-exp-dt6"][0]
if not good:
    ok = False
print("== differences")
p = compare("patchy-imp-dt6", "patchy-exp-dt3", "patchy, implicit DT 6 s vs explicit DT 3 s")
compare("patchy-imp-dt3", "patchy-exp-dt3", "patchy, implicit DT 3 s vs explicit DT 3 s")
compare("const-imp-dt6", "const-exp-dt6", "uniform canopy, implicit vs explicit DT 6 s")
ok &= p <= TOL
print(f"explicit DT 6 s on the patchy canopy: {'blew up' if st['patchy-exp-dt6'][3] else 'did not blow up'}")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
