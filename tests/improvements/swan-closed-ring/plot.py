"""Figure of the swan-closed-ring test (Circle_Island runs of run.sh).

    python -I plot.py OUTDIR FIGURE.png [GRID]

Coordinates come from GRID (default: tests/cases/Circle_Island/circle_grid.nc).

Panels: the grid and its depth; Hs and depth-mean current with waves from
the north; the difference made by moving the seam 90 degrees; Hs with waves
from all sides (inward) and its departure from the mean round each ring.
"""
import sys
from pathlib import Path

import matplotlib
import netCDF4
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LM = 216
GRID = Path(__file__).resolve().parents[2] / "cases" / "Circle_Island" / "circle_grid.nc"


def load(run, rec=-1, grid=GRID):
    with netCDF4.Dataset(grid) as d:
        g = {k: d[k][:].astype(float) for k in ("x_psi", "y_psi", "x_rho", "y_rho", "h", "angle")}
    with netCDF4.Dataset(run / "output" / "ocean_his.nc") as d:
        m = d["mask_rho"][:] > 0
        f = {k: np.ma.filled(d[k][rec].astype(float), np.nan) for k in ("Hwave", "zeta", "ubar", "vbar")}
    for k in ("Hwave", "zeta"):
        f[k] = np.where(m, f[k], np.nan)
    u = 0.5 * (f["ubar"][:, :-1] + f["ubar"][:, 1:])          # u columns i-1, i -> rho column i (1..Lm)
    v = 0.5 * (f["vbar"][:-1] + f["vbar"][1:])                # v rows j, j+1 -> rho row j (1..Mm)
    ur = np.full(m.shape, np.nan)
    vr = np.full(m.shape, np.nan)
    ur[:, 1:-1] = u
    vr[1:-1] = v[:, :]
    a = g["angle"]
    f["ue"] = np.where(m, ur * np.cos(a) - vr * np.sin(a), np.nan)
    f["vn"] = np.where(m, ur * np.sin(a) + vr * np.cos(a), np.nan)
    return g, f, m


def ring(a):
    """Close a rho field (columns 1..Lm) for plotting on the psi mesh."""
    return a[1:-1, 1:LM + 1]


def mesh(g):
    """psi corners round each rho cell of rows 1..Mm, columns 1..Lm (closing the ring)."""
    xp = np.concatenate([g["x_psi"], g["x_psi"][:, :1]], axis=1)[:, :LM + 1]
    yp = np.concatenate([g["y_psi"], g["y_psi"][:, :1]], axis=1)[:, :LM + 1]
    return xp / 1e3, yp / 1e3


def main():
    out, fig_path = Path(sys.argv[1]), Path(sys.argv[2])
    grid = Path(sys.argv[3]) if len(sys.argv) > 3 else GRID
    g, fn, m = load(out / "north", grid=grid)
    xp, yp = mesh(g)
    fig, ax = plt.subplots(2, 2, figsize=(12, 11), constrained_layout=True)
    seam = (g["x_psi"][:, 0] / 1e3, g["y_psi"][:, 0] / 1e3)

    a = ax[0, 0]
    pc = a.pcolormesh(xp, yp, ring(np.where(m, g["h"], np.nan)), cmap="Blues", vmax=30)
    fig.colorbar(pc, ax=a, label="depth (m)")
    for j in range(0, xp.shape[0], 4):
        a.plot(xp[j], yp[j], "k-", lw=0.2)
    for i in range(0, LM, 6):
        a.plot(xp[:, i], yp[:, i], "k-", lw=0.2)
    a.plot(*seam, "r-", lw=1.5, label="seam (between columns 216 and 1)")
    a.set_title("O-grid: every 4th ring, every 6th spoke")
    a.legend(loc="lower left")

    a = ax[0, 1]
    pc = a.pcolormesh(xp, yp, ring(fn["Hwave"]), cmap="viridis")
    fig.colorbar(pc, ax=a, label="Hs (m)")
    xr, yr = g["x_rho"] / 1e3, g["y_rho"] / 1e3
    s = (slice(1, 50, 2), slice(1, LM + 1, 3))
    a.quiver(xr[s], yr[s], fn["ue"][s], fn["vn"][s], scale=8, width=0.002, color="w")
    a.plot(*seam, "r-", lw=1.5)
    a.set_title("waves from the north: Hs, current (arrows)")

    a = ax[1, 0]
    if (out / "north-roll54").exists():
        _, fr, _ = load(out / "north-roll54", grid=grid)
        back = np.full_like(fn["Hwave"], np.nan)
        back[:, 1:LM + 1] = np.roll(fr["Hwave"][:, 1:LM + 1], 54, axis=1)
        dh = back - fn["Hwave"]
        lim = np.nanmax(np.abs(dh[:, 1:LM + 1])) or 1e-9
        pc = a.pcolormesh(xp, yp, ring(dh), cmap="RdBu_r", vmin=-lim, vmax=lim)
        fig.colorbar(pc, ax=a, label="Hs, seam moved minus reference (m)")
        a.plot(*seam, "k-", lw=1, label="reference seam")
        a.plot(g["x_psi"][:, 54] / 1e3, g["y_psi"][:, 54] / 1e3, "k--", lw=1, label="moved seam")
        a.legend(loc="lower left")
        a.set_title("seam moved 90 degrees, mapped back")

    a = ax[1, 1]
    if (out / "inward").exists():
        _, fi, mi = load(out / "inward", grid=grid)
        hs = fi["Hwave"]
        with np.errstate(invalid="ignore"):
            dev = hs - np.nanmean(hs[:, 1:LM + 1], axis=1, keepdims=True)
        lim = np.nanmax(np.abs(dev[:, 1:LM + 1])) or 1e-9
        pc = a.pcolormesh(xp, yp, ring(dev), cmap="RdBu_r", vmin=-lim, vmax=lim)
        fig.colorbar(pc, ax=a, label=f"Hs minus its mean round the ring (m); Hs {np.nanmin(hs):.2f}-{np.nanmax(hs):.2f} m")
        a.plot(*seam, "k-", lw=1)
        a.set_title("waves from all sides: Hs minus ring mean")
    for a in ax.flat:
        a.set_aspect("equal")
        a.set_xlabel("x (km)")
        a.set_ylabel("y (km)")
    for a in (ax[0, 1], ax[1, 0], ax[1, 1]):
        a.set_xlim(-2.5, 2.5)
        a.set_ylim(-2.5, 2.5)
    fig.savefig(fig_path, dpi=110)
    print(f"wrote {fig_path}")


if __name__ == "__main__":
    main()
