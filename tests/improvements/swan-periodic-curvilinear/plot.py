"""Figure for 2-improvements/swan-periodic-curvilinear.patch.

    python -I plot.py OUTDIR FIGURE.png

OUTDIR as written by run.sh. Top left: Hs on the periodic stretched grid
(pass in the middle). Top right: the run with the seam through the pass minus
the middle run rolled by half a period (4 processes): the seam leaves only
SWAN's iteration error. Bottom left: non-periodic minus periodic, the shadow
of the side walls that the periodic boundary removes. Bottom right: the
uniform grid given as curvilinear minus as regular (zero).
Needs numpy, netCDF4 and matplotlib.
"""
import sys
from pathlib import Path

import matplotlib
import netCDF4
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

out, fig_path = Path(sys.argv[1]), sys.argv[2]


def field(run, fname="hsign.nc"):
    with netCDF4.Dataset(out / run / "output" / fname) as d:
        v = [v for v in d.variables.values() if v.ndim == 3][0]
        return np.ma.filled(v[-1].astype(float), np.nan)


coords = np.loadtxt(out / "str-mid-np1" / "coord.grd")
ny = coords.shape[0] // 2
xs, ys = coords[0], coords[ny:, 0]
mid = field("str-mid-np1")
n = mid.shape[1]
X, Y = np.meshgrid(xs[:n], ys)
panels = [
    (mid, "Hs, periodic stretched grid, pass in the middle", "viridis", False),
    (field("str-seam-np4") - np.roll(field("str-mid-np4"), -n // 2, axis=1),
     "seam through the pass - middle rolled (4 processes)", "RdBu_r", True),
    (field("str-norep-np1")[:, :n] - mid, "non-periodic - periodic", "RdBu_r", True),
    (field("uni-crv-mid-np1") - field("uni-reg-mid-np1"), "uniform grid: curvilinear - regular", "RdBu_r", True),
]
fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
for ax, (f, title, cmap, sym) in zip(axes.flat, panels):
    if "uniform grid" in title:
        m = ax.pcolormesh(f, cmap=cmap, vmin=-1e-6, vmax=1e-6)
        ax.set_xlabel("alongshore index")
        ax.set_ylabel("cross-shore index")
    else:
        lim = (np.nanmax(np.abs(f)) or 1e-12) if sym else None
        m = ax.pcolormesh(X, Y, f, cmap=cmap, vmin=-lim if sym else None, vmax=lim, shading="nearest")
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
    fig.colorbar(m, ax=ax, label="Hs (m)" if not sym else "dHs (m)")
    ax.set_title(title)
fig.suptitle("swan-periodic-curvilinear: standalone SWAN, A15-like reef with a pass, 1 h")
fig.savefig(fig_path, dpi=110)
print(f"wrote {fig_path}")
