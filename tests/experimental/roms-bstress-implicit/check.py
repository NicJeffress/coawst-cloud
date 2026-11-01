"""Checks of 3-experimental/roms-bstress-implicit.patch (runs of run.sh).

    python -I check.py OUTDIR

For a15-exp/a15-imp and circle-cap/circle-imp: whether each run finished,
and at the last common record the differences in depth-mean current (at rho
points), sea level and Hs (largest, 99.9th percentile), and the largest
bottom stress magnitude (99.9th percentile and largest, wet points) in each run. PASS if both A15 runs finished.
"""
import re
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])


def finished(run):
    info = (run / "image_info.txt").read_text() if (run / "image_info.txt").exists() else ""
    log = (run / "log.txt").read_text(errors="replace") if (run / "log.txt").exists() else ""
    t = t0 = None
    if (run / "output/ocean_his.nc").exists():
        with Dataset(run / "output/ocean_his.nc") as d:
            t, t0 = float(d["ocean_time"][-1]), float(d["ocean_time"][0])
    return "exit 0" in info and "Blowing-up" not in log, t, t0


def fields(run, t):
    with Dataset(run / "output/ocean_his.nc") as d:
        k = [float(x) for x in d["ocean_time"][:]].index(t)
        m = d["mask_rho"][:] > 0
        ub = np.ma.filled(d["ubar"][k].astype(float), np.nan)
        vb = np.ma.filled(d["vbar"][k].astype(float), np.nan)
        u = np.full(m.shape, np.nan)
        v = np.full(m.shape, np.nan)
        u[:, 1:-1] = 0.5 * (ub[:, :-1] + ub[:, 1:])
        v[1:-1] = 0.5 * (vb[:-1] + vb[1:])
        bu = np.ma.filled(d["bustr"][k].astype(float), 0.0)        # u points (eta_rho, xi_u)
        bv = np.ma.filled(d["bvstr"][k].astype(float), 0.0)        # v points (eta_v, xi_rho)
        bs = np.hypot(0.5 * (bu[1:-1, :-1] + bu[1:-1, 1:]), 0.5 * (bv[:-1, 1:-1] + bv[1:, 1:-1]))
        f = {"u": u, "v": v, "zeta": np.ma.filled(d["zeta"][k].astype(float), np.nan),
             "Hwave": np.ma.filled(d["Hwave"][k].astype(float), np.nan)}
        wet = m[1:-1, 1:-1]
        return ({n: np.where(m, a, np.nan)[1:-1, 1:-1] for n, a in f.items()},
                (float(np.percentile(bs[wet], 99.9)), float(bs[wet].max())))


ok = True
for a, b in (("a15-exp", "a15-imp"), ("circle-cap", "circle-imp")):
    sa, sb = finished(out / a), finished(out / b)
    rel = lambda st: None if st[1] is None else (st[1] - st[2]) / 60
    print(f"== {a}: {'finished' if sa[0] else 'stopped'} (last output {rel(sa)} min); "
          f"{b}: {'finished' if sb[0] else 'stopped'} (last output {rel(sb)} min)")
    if a.startswith("a15"):
        ok &= sa[0] and sb[0]
    if sa[1] is None or sb[1] is None:
        continue
    t = min(sa[1], sb[1])
    fa, ta = fields(out / a, t)
    fb, tb = fields(out / b, t)
    du = np.hypot(fa["u"] - fb["u"], fa["v"] - fb["v"])
    du = du[np.isfinite(du)]
    print(f"   at {(t - sa[2]) / 60:.0f} min: current difference largest {du.max():.3f} m/s, 99.9th pct "
          f"{np.percentile(du, 99.9):.4f} m/s; sea level {np.nanmax(np.abs(fa['zeta'] - fb['zeta'])):.1e} m; "
          f"Hs {np.nanmax(np.abs(fa['Hwave'] - fb['Hwave'])):.3f} m; bottom stress at wet points, 99.9th pct / largest: "
          f"{a} {ta[0]:.2f} / {ta[1]:.2f}, {b} {tb[0]:.2f} / {tb[1]:.2f} N m-2")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
