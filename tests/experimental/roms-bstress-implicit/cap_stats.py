"""Bottom-stress stability number on the crest at the last record.
S = tau_kin * DT / (Hz_1 |u_1|): LIMIT_BSTRESS caps it at 0.75.
    python -I cap_stats.py RUNDIR...   (run folders as for thin_crest_summary.py)
"""
import sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
RHO0 = 1025.0
for run in sys.argv[1:]:
    run = Path(run) / "task0" if (Path(run) / "task0").exists() else Path(run)
    his = run / "output/ocean_his.nc"
    info = (run / "image_info.txt").read_text()
    dt = float(info.split("DT ")[1].split()[0])
    with Dataset(his) as d:
        r = len(d["ocean_time"]) - 1
        h = np.ma.filled(d["h"][:].astype(float), 0); m = np.ma.filled(d["mask_rho"][:], 0) > 0
        hc = float(d["hc"][:]); sw = np.ma.filled(d["s_w"][:], 0); cw = np.ma.filled(d["Cs_w"][:], 0)
        z = np.ma.filled(d["zeta"][r].astype(float), 0)
        zw = z[None] + (z + h)[None] * (hc * sw[:, None, None] + h[None] * cw[:, None, None]) / (hc + h)[None]
        hz1 = zw[1] - zw[0]
        u = np.ma.filled(d["u"][r, 0].astype(float), 0); v = np.ma.filled(d["v"][r, 0].astype(float), 0)
        ur = np.zeros(h.shape); vr = np.zeros(h.shape)
        ur[:, 1:-1] = 0.5 * (u[:, :-1] + u[:, 1:]); vr[1:-1] = 0.5 * (v[:-1] + v[1:])
        u1 = np.hypot(ur, vr)
        bu = np.ma.filled(d["bustr"][r].astype(float), 0); bv = np.ma.filled(d["bvstr"][r].astype(float), 0)
        tau = np.zeros(h.shape)
        tau[1:-1, 1:-1] = np.hypot(0.5 * (bu[1:-1, :-1] + bu[1:-1, 1:]), 0.5 * (bv[:-1, 1:-1] + bv[1:, 1:-1])) / RHO0
        reef = (h[32] < 0.8)
        for name, rows in (("crest (h<0.8, rows 30-35)", slice(30, 36)), ("flanks/lagoon rows 36-40", slice(36, 41))):
            sel = np.zeros(h.shape, bool); sel[rows, reef] = True; sel &= m & (h < 0.8 if "crest" in name else True) & (u1 > 0.01)
            S = tau[sel] * dt / (hz1[sel] * u1[sel])
            print(f"{run.parent.name if run.name == 'task0' else run.name:28s} {name:26s} n={sel.sum():5d} Hz1 {np.median(hz1[sel])*100:4.1f} cm |u1| med {np.median(u1[sel]):.3f} m/s "
                  f"tau med {np.median(tau[sel])*RHO0:.2f} N/m2  S med {np.median(S):.2f} p90 {np.percentile(S,90):.2f} max {S.max():.1f}  frac S>=0.74: {np.mean(S>=0.74):.2f}")
