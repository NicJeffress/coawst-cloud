"""Figure for 1-fixes/roms-sed-morph-tiling.patch.

    python -I plot_tiling.py OUTDIR FIGURE.png

OUTDIR as written by run.sh (before_1x1, before_1x2, after_1x1, after_1x2).
Left: bathymetry difference 1x1 - 1x2 tiles at the last record, before the
patch (the tile edge is marked). Middle: the largest difference against time,
before and after. Right: the bathymetry, for orientation.
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


def bath(run):
    d = Dataset(out / run / "ocean_his_coupled.nc")
    return d["ocean_time"][:] / 3600.0, np.ma.filled(d["bath"][:], np.nan), d


t, b11, d = bath("before_1x1")
_, b12, _ = bath("before_1x2")
_, a11, _ = bath("after_1x1")
_, a12, _ = bath("after_1x2")
x, y = d["x_rho"][:] / 1e3, d["y_rho"][:] / 1e3
diff = (b11[-1] - b12[-1]) * 1000.0
mj = d["bath"].shape[1]
edge = y[mj // 2, 0]                       # 1x2 tiles: split in j at the middle
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
lim = float(np.nanmax(np.abs(diff)))
m = ax[0].pcolormesh(x, y, diff, cmap="RdBu_r", vmin=-lim, vmax=lim, shading="auto")
ax[0].axhline(edge, color="k", ls=":", lw=1)
ax[0].text(x.min() + 0.2, edge + 0.15, "tile edge (1x2)", fontsize=8)
fig.colorbar(m, ax=ax[0], label="mm")
ax[0].set_title(f"Before the patch: bathymetry 1x1 - 1x2 tiles at {t[-1]:.0f} h")
ax[0].set_xlabel("x (km)")
ax[0].set_ylabel("y (km)")
for b1, b2, label, c in ((b11, b12, "before the patch", "#c0392b"), (a11, a12, "after the patch", "#2471a3")):
    md = [float(np.nanmax(np.abs(b1[k] - b2[k]))) * 1000.0 for k in range(len(t))]
    ax[1].plot(t, md, "o-", color=c, label=label)
ax[1].set_xlabel("time (h)")
ax[1].set_ylabel("max |bathymetry 1x1 - 1x2| (mm)")
ax[1].set_title("Largest tiling difference")
ax[1].legend()
m = ax[2].pcolormesh(x, y, b11[-1], cmap="viridis_r", shading="auto")
fig.colorbar(m, ax=ax[2], label="depth (m)")
ax[2].axhline(edge, color="w", ls=":", lw=1)
ax[2].set_title("Inlet_test bathymetry")
ax[2].set_xlabel("x (km)")
fig.savefig(fig_path, dpi=110)
print(f"wrote {fig_path}")
