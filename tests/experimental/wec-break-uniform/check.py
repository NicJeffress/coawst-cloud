"""Checks of 3-experimental/wec-break-uniform.patch (runs of run.sh).

    python -I check.py OUTDIR

OUTDIR/default and OUTDIR/uniform. In the last diagnostics record, at the 50
v-points with the largest depth-integrated breaking acceleration |v_wbrk|,
the ratio of the top-layer to the bottom-layer breaking acceleration (median
and range). Also the difference in depth-mean current and in the surface and
bottom currents at the last history record.
PASS if the uniform profile's ratio is 1 within 1 % at all those points and
the default's median ratio is above 2.
"""
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])


def ratios(run):
    with Dataset(run / "output/ocean_dia.nc") as d:
        w = np.ma.filled(d["v_wbrk"][-1].astype(float), 0.0)   # (N, eta_v, xi_v)
    tot = np.abs(w).sum(axis=0)
    idx = np.argsort(tot.ravel())[::-1][:50]
    j, i = np.unravel_index(idx, tot.shape)
    top, bot = w[-1, j, i], w[0, j, i]
    return top / np.where(bot == 0, np.nan, bot)


ok = True
r = {v: ratios(out / v) for v in ("default", "uniform")}
for v, a in r.items():
    print(f"{v:8s} top/bottom breaking acceleration at the 50 strongest points: median {np.nanmedian(a):.3f}, "
          f"range {np.nanmin(a):.3f} - {np.nanmax(a):.3f}")
ok &= bool(np.all(np.abs(r["uniform"] - 1) < 0.01)) and np.nanmedian(r["default"]) > 2
with Dataset(out / "default/output/ocean_his.nc") as a, Dataset(out / "uniform/output/ocean_his.nc") as b:
    for v in ("ubar", "vbar"):
        x = np.ma.filled(a[v][-1].astype(float), np.nan)
        y = np.ma.filled(b[v][-1].astype(float), np.nan)
        print(f"{v}: largest difference {np.nanmax(np.abs(x - y)):.3f} m/s (largest |{v}| {np.nanmax(np.abs(x)):.3f})")
    for v in ("u", "v"):
        for k, name in ((-1, "surface"), (0, "bottom")):
            x = np.ma.filled(a[v][-1, k].astype(float), np.nan)
            y = np.ma.filled(b[v][-1, k].astype(float), np.nan)
            print(f"{v} {name}: largest difference {np.nanmax(np.abs(x - y)):.3f} m/s")
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
