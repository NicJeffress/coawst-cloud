"""Figure for tau_veg_units (1-fixes/roms-vegetation.patch).

    python -I plot_units_effect.py OUTDIR FIGURE.png

OUTDIR as written by run.sh (after/, nounits/). Left: distribution of the
ratio of the canopy eddy viscosity AKv with the units fix to AKv without it
(w points inside the 0.4 m canopy, last record). Right: median AKv against
height above the bed in the canopy, with and without the fix.
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
a, b = Dataset(out / "after/output/ocean_his.nc"), Dataset(out / "nounits/output/ocean_his.nc")
akv_a, akv_b = np.ma.filled(a["AKv"][-1], np.nan), np.ma.filled(b["AKv"][-1], np.nan)
h = a["h"][:]
hc, sw, cw = float(a["hc"][:]), np.asarray(a["s_w"][:]), np.asarray(a["Cs_w"][:])
above = (hc * sw[:, None, None] + h[None] * cw[:, None, None]) * h[None] / (hc + h[None]) + h[None]
canopy = (above > 0.01) & (above < 0.4)
r = (akv_a / akv_b)[canopy]
r = r[np.isfinite(r)]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
ax[0].hist(r, bins=np.linspace(0.6, 1.2, 61), color="#2471a3")
q = np.percentile(r, [10, 50, 90])
for v, s in zip(q, ("10 %", "median", "90 %")):
    ax[0].axvline(v, color="k", ls="--" if s != "median" else "-", lw=1)
    ax[0].text(v, ax[0].get_ylim()[1] * 0.95, f" {s}\n {v:.3f}", fontsize=8, va="top")
ax[0].set_xlabel("AKv with the units fix / AKv without it")
ax[0].set_ylabel("canopy w points")
ax[0].set_title("Canopy eddy viscosity after 1 h (Reef_Ideal_A15_veg)")
bins = np.linspace(0.0, 0.4, 9)
mid = 0.5 * (bins[1:] + bins[:-1])
for akv, label, c in ((akv_b, "without the fix (COAWST)", "#c0392b"), (akv_a, "with the fix", "#2471a3")):
    med = [np.nanmedian(akv[(above >= lo) & (above < hi)]) for lo, hi in zip(bins[:-1], bins[1:])]
    ax[1].plot(med, mid, "o-", color=c, label=label)
ax[1].set_xscale("log")
ax[1].set_xlabel("median AKv (m2/s)")
ax[1].set_ylabel("height above the bed (m); canopy top 0.4 m")
ax[1].set_title("Median eddy viscosity in the canopy")
ax[1].legend()
fig.savefig(fig_path, dpi=110)
print(f"wrote {fig_path}: ratio 10/50/90 % = {q[0]:.3f} / {q[1]:.3f} / {q[2]:.3f}")
