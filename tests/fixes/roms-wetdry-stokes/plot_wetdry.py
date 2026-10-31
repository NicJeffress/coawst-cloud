"""Figure for 1-fixes/roms-wetdry-stokes.patch.

    python -I plot_wetdry.py OUTDIR FIGURE.png

OUTDIR as written by run.sh (wd-before, wd-after, nowd-after). Left: largest
difference in the depth-mean current between the run with WET_DRY and the run
without it, against time, before and after the patch (log scale). Middle and
right: the difference in vbar at the last record, before and after, same
colour scale.
Needs numpy, netCDF4 and matplotlib.
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np
from netCDF4 import Dataset

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

out, fig_path = Path(sys.argv[1]), sys.argv[2]
ref = Dataset(out / "nowd-after/output/ocean_his.nc")
t = ref["ocean_time"][:] / 60.0
x, y = ref["x_v"][:] / 1e3, ref["y_v"][:] / 1e3
h = ref["h"][:]
xr, yr = ref["x_rho"][:] / 1e3, ref["y_rho"][:] / 1e3
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
dv = {}
for side, c in (("before", "#c0392b"), ("after", "#2471a3")):
    d = Dataset(out / f"wd-{side}/output/ocean_his.nc")
    m = [max(float(np.nanmax(np.abs(np.ma.filled(d[v][k], np.nan) - np.ma.filled(ref[v][k], np.nan))))
             for v in ("ubar", "vbar")) for k in range(len(t))]
    ax[0].semilogy(t[1:], m[1:], "o-", color=c, label=f"WET_DRY {side} the patch")
    dv[side] = np.ma.filled(d["vbar"][-1], np.nan) - np.ma.filled(ref["vbar"][-1], np.nan)
ax[0].set_xlabel("time (min)")
ax[0].set_ylabel("max |difference| in ubar, vbar (m/s)")
ax[0].set_title("WET_DRY on vs off (nothing dries in this case)")
ax[0].legend()
lim = float(np.nanmax(np.abs(dv["before"])))
for a, side in zip(ax[1:], ("before", "after")):
    p = a.pcolormesh(x, y, dv[side], cmap="RdBu_r", vmin=-lim, vmax=lim, shading="auto")
    a.contour(xr, yr, h, levels=[1.0], colors="k", linewidths=0.5)
    a.set_ylim(0, 2.0)
    a.set_title(f"{side} the patch: vbar, WET_DRY - no WET_DRY, {t[-1]:.0f} min", fontsize=10)
    a.set_xlabel("x (km, alongshore)")
ax[1].set_ylabel("y (km, cross-shore)")
fig.colorbar(p, ax=ax[1:], label="m/s (black: 1 m depth contour, the reef crest)")
fig.savefig(fig_path, dpi=110)
print(f"wrote {fig_path}")
