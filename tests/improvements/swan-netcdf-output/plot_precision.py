"""Figure for 2-improvements/swan-netcdf-output.patch.

    python -I plot_precision.py OUTDIR FIGURE.png

OUTDIR as written by run.sh. Left: Hs from the .nc file minus Hs from the
.mat file of the same run, at 1 h, without the patch (16-bit packing: a
staircase of steps of 0.76 mm, errors up to half a step). Middle: the same
difference against Hs, before (dots) and after (zero). Right: a quantity
stock SWAN refused as NetCDF, total dissipation DISSIP, from the .nc file
written with the patch. Needs numpy, netCDF4, scipy and matplotlib.
"""
import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
from netCDF4 import Dataset
from scipy.io import loadmat

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.simplefilter("ignore")
out, fig_path = Path(sys.argv[1]), sys.argv[2]


def hs_pair(run):
    nc = np.ma.filled(Dataset(out / run / "n_hsign.nc")["hs"][-1].astype(float), np.nan)
    m = loadmat(out / run / "m_hsign.mat")
    mat = np.asarray(m[sorted(k for k in m if k.startswith("Hsig"))[-1]], dtype=float)
    mat[mat < -9e3] = np.nan
    return nc, mat


nb, mb = hs_pair("before-same")
na, ma = hs_pair("after-same")
d = Dataset(out / "after-all" / "n_dissip.nc")
x, y = d["x"][:] / 1e3, d["y"][:] / 1e3
diss = np.ma.filled(d["dissip"][-1].astype(float), np.nan)

fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
err = (nb - mb) * 1000.0
m0 = ax[0].pcolormesh(x, y, err, cmap="RdBu_r", vmin=-0.4, vmax=0.4, shading="auto")
fig.colorbar(m0, ax=ax[0], label="Hs .nc - .mat (mm)")
ax[0].set_title("Without the patch: Hs stored as 16-bit integers")
ax[1].plot(mb.ravel(), err.ravel(), ".", ms=2, color="tab:red", label="without the patch")
ax[1].plot(ma.ravel(), ((na - ma) * 1000.0).ravel(), ".", ms=2, color="tab:blue", label="with the patch (float)")
ax[1].axhline(0.38, color="k", ls=":", lw=1)
ax[1].axhline(-0.38, color="k", ls=":", lw=1)
ax[1].set_xlabel("Hs (m)")
ax[1].set_ylabel("Hs .nc - .mat (mm)")
ax[1].set_title("Error against Hs (dotted: half the 0.76 mm step)")
ax[1].legend(loc="upper right", markerscale=4)
m2 = ax[2].pcolormesh(x, y, diss, cmap="viridis", shading="auto")
fig.colorbar(m2, ax=ax[2], label="W m-2")
ax[2].set_title("DISSIP as NetCDF (refused without the patch)")
for a in (ax[0], ax[2]):
    a.set_xlabel("x (km)")
    a.set_ylabel("y (km)")
    a.set_aspect("equal")
fig.suptitle("swan-netcdf-output: Inlet_test after 1 h, BLOCK output as .nc and .mat")
fig.savefig(fig_path, dpi=110)
print(f"wrote {fig_path}")
