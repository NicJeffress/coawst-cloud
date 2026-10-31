"""Figure for the coupled A15 test of periodic_coupled_stokes.

    python -I plot_a15_coupled.py OUTDIR FIGURE.png

OUTDIR as written by run_a15_coupled.sh (before/, after/). Left: the largest
Stokes drift in the domain against time, before and after the fix. Middle and
right: depth-averaged Stokes drift speed at 30 min, before and after, in the
same colour scale, with the crest rows and the pass marked.
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
runs = {}
for side in ("before", "after"):
    d = Dataset(out / side / "output" / "ocean_his.nc")
    t = d["ocean_time"][:] / 60.0
    us = np.ma.filled(d["ubar_stokes"][:], np.nan)
    vs = np.ma.filled(d["vbar_stokes"][:], np.nan)
    u3 = np.ma.filled(d["u_stokes"][:], np.nan)
    v3 = np.ma.filled(d["v_stokes"][:], np.nan)
    smax = [max(np.nanmax(np.abs(u3[k])), np.nanmax(np.abs(v3[k]))) for k in range(len(t))]
    k30 = int(np.argmin(np.abs(t - 30)))
    # depth-averaged Stokes speed on rho points at 30 min
    u = 0.5 * (us[k30][:, :-1] + us[k30][:, 1:])
    v = 0.5 * (vs[k30][:-1, :] + vs[k30][1:, :])
    sp = np.hypot(u[1:-1, :], v[:, 1:-1])
    runs[side] = dict(t=t, smax=smax, sp=sp, x=d["x_rho"][1:-1, 1:-1] / 1e3, y=d["y_rho"][1:-1, 1:-1] / 1e3,
                      h=d["h"][1:-1, 1:-1])

fig, ax = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
for side, c in (("before", "#c0392b"), ("after", "#2471a3")):
    r = runs[side]
    ax[0].plot(r["t"], r["smax"], "o-", color=c, label=f"{side} the fix")
ax[0].axvline(35.2, color="#c0392b", ls=":", lw=1)
ax[0].text(35.6, 1.2, "before: ROMS\nblows up\nat 35 min", color="#c0392b", fontsize=9)
ax[0].set_xlabel("time (min)")
ax[0].set_ylabel("largest Stokes drift (m/s)")
ax[0].set_title("Largest Stokes drift in the domain")
ax[0].legend()
vmax = float(np.nanpercentile(runs["before"]["sp"], 99.9))
for a, side in zip(ax[1:], ("before", "after")):
    r = runs[side]
    m = a.pcolormesh(r["x"], r["y"], r["sp"], vmin=0, vmax=vmax, cmap="magma", shading="auto")
    a.contour(r["x"], r["y"], r["h"], levels=[1.0], colors="w", linewidths=0.6)
    a.set_title(f"{side} the fix: depth-mean Stokes drift at 30 min")
    a.set_xlabel("x (km, alongshore)")
    a.set_ylim(0, 2.0)
ax[1].set_ylabel("y (km, cross-shore)")
fig.colorbar(m, ax=ax[1:], label="m/s (white: 1 m depth contour, the reef crest)")
fig.savefig(fig_path, dpi=110)
print(f"wrote {fig_path}")
