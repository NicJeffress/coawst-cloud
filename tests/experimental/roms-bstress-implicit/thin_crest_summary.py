"""Summarize thin-crest Reef_Ideal_A15 bottom-stress runs (thin_crest.sh).

    python -I thin_crest_summary.py RUNDIR...
(each holds image_info.txt, log.txt and output/ocean_his.nc, directly or under task0/)

Per run: finished or blow-up time (log), then per history record the fastest
3-D current (value, i, j, k), the largest |w| with its vertical Courant number
|w| DT / dz, the largest bottom stress, the crest depth-mean current (row 33,
reef columns) and the lagoon set-up (rows 5-25 minus rows 95-105).
"""
import re, sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

def one(run):
    run = Path(run)
    t0 = run / "task0" if (run / "task0").exists() else run
    info = (t0 / "image_info.txt").read_text() if (t0 / "image_info.txt").exists() else ""
    log = (t0 / "log.txt").read_text(errors="replace") if (t0 / "log.txt").exists() else ""
    dt = float(re.search(r"DT ([0-9.]+) s", info).group(1)) if "DT " in info else 6.0
    blow = "Blowing-up" in log
    steps = re.findall(r"^\s*(\d+)\s+(\d+) (\d\d:\d\d:\d\d)\s", log, re.M)
    last = steps[-1] if steps else None
    print(f"\n== {run.name}: {'BLOW-UP' if blow else ('finished' if 'exit 0' in info else 'stopped')}"
          f"{'' if last is None else f', last step {last[0]} at day {last[1]} {last[2]}'}; {info.strip().splitlines()[-1] if info else ''}")
    his = t0 / "output/ocean_his.nc"
    if not his.exists():
        return
    with Dataset(his) as d:
        h = np.ma.filled(d["h"][:].astype(float), 0); m = np.ma.filled(d["mask_rho"][:], 0) > 0
        hc = float(d["hc"][:]); sw = np.ma.filled(d["s_w"][:], 0); cw = np.ma.filled(d["Cs_w"][:], 0)
        reef = (h[32] < 0.8)
        print("  rec  min   maxspd  (i,j,k)   max|w|   Cw   (i,j,k)   bstr99.9 bstrmax  crest v  setup(mm)")
        for r in range(len(d["ocean_time"])):
            t = float(d["ocean_time"][r]) / 60
            u = np.ma.filled(d["u"][r].astype(float), 0); v = np.ma.filled(d["v"][r].astype(float), 0)
            ur = np.zeros(u.shape[:1] + h.shape); vr = np.zeros_like(ur)
            ur[:, :, 1:-1] = 0.5 * (u[:, :, :-1] + u[:, :, 1:]); vr[:, 1:-1] = 0.5 * (v[:, :-1] + v[:, 1:])
            spd = np.hypot(ur, vr) * m
            k, j, i = np.unravel_index(spd.argmax(), spd.shape)
            z = np.ma.filled(d["zeta"][r].astype(float), 0)
            zw = z[None] + (z + h)[None] * (hc * sw[:, None, None] + h[None] * cw[:, None, None]) / (hc + h)[None]
            dz = np.diff(zw, axis=0)
            w = np.abs(np.ma.filled(d["w"][r].astype(float), 0)) * m   # at w points (N+1)
            dzw = np.concatenate([dz[:1], 0.5 * (dz[:-1] + dz[1:]), dz[-1:]], axis=0)
            cwn = w * dt / dzw
            kw, jw, iw = np.unravel_index(cwn.argmax(), cwn.shape)
            bu = np.ma.filled(d["bustr"][r].astype(float), 0); bv = np.ma.filled(d["bvstr"][r].astype(float), 0)
            bs = np.hypot(0.5 * (bu[1:-1, :-1] + bu[1:-1, 1:]), 0.5 * (bv[:-1, 1:-1] + bv[1:, 1:-1]))[m[1:-1, 1:-1]]
            vb = np.ma.filled(d["vbar"][r].astype(float), 0)
            crest = np.nanmean(vb[32, reef[:]])  # vbar at v row 32 lies between rho rows 32 and 33
            setup = 1000 * (np.nanmean(np.where(m, z, np.nan)[5:26]) - np.nanmean(np.where(m, z, np.nan)[95:106]))
            print(f"  {r:3d} {t:5.0f} {spd.max():7.2f} ({i:3d},{j:3d},{k+1:2d}) {w.max():7.3f} {cwn.max():6.2f} ({iw:3d},{jw:3d},{kw:2d})"
                  f" {np.percentile(bs, 99.9):7.2f} {bs.max():7.2f} {crest:8.3f} {setup:8.1f}")

for r in sys.argv[1:]:
    one(r)
