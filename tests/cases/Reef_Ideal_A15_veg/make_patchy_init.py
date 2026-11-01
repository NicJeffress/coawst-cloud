"""Initial file of Reef_Ideal_A15_veg with a patchy canopy.

Usage:
  python3 -I make_patchy_init.py [OUT.nc]     (default: init_reef_patchy.nc here)

The case's own init_reef.nc has the same plants everywhere. This writes a
copy with a patchy reef: over the backreef, crest and forereef, 30 % of the
area dense plants (4 m-2), 30 % sparse (1 m-2), 40 % bare, in patches of
about 150 m; lagoon, pass and deep water bare. Plants are cylinders, 0.5 m
in diameter and 0.4 m high, with thickness pi/4 x diameter (so diameter x
thickness is their cross-section). Dense patches give 0.5 Cd D n = 1 m-1,
so with currents near 1 m/s the explicit drag is unstable at the case's
DT of 6 s (the tests of 3-experimental/roms-veg-implicit).

Reef zones come from depth and the side of the reef crest: the crest line
is the middle of the shallowest band in each column (columns without one,
in the pass, take the nearest column's), the pass is where the depth is more
than 1 m below the median depth of its row, crest h <= 1 m, backreef h <= 5 m
landward of the crest, forereef h <= 20 m seaward. The patches are a smooth
random field (Gaussian, sigma = 150 m / 3, seed 1, periodic in x) whose
highest values become dense, the next sparse.
"""
import shutil
import sys
from pathlib import Path

import netCDF4
import numpy as np
from scipy import ndimage
from scipy.interpolate import RegularGridInterpolator

HERE = Path(__file__).resolve().parent
CLASSES = {"bare": (0.0, 0.0, 0.0), "sparse": (1.0, 0.5, 0.4), "dense": (4.0, 0.5, 0.4)}  # n, D, height
COVER = {"dense": 0.3, "sparse": 0.3}
SIZE_M, SEED = 150.0, 1
CREST, BACKREEF, FOREREEF, PASS_EXCESS = 1.0, 5.0, 20.0, 1.0


def ghosts(a):
    """EW periodic: columns 0 and Lm+1 are copies of Lm and 1."""
    a[..., 0] = a[..., -2]
    a[..., -1] = a[..., 1]
    return a


def reef_mask(h, wet):
    hw = np.where(wet, h, np.nan)
    ny, nx = h.shape
    profile = np.full(ny, np.nan)
    rows_wet = wet[:, 1:-1].any(axis=1)
    profile[rows_wet] = np.nanmedian(hw[rows_wet, 1:-1], axis=1)
    deeper = hw - profile[:, None] > PASS_EXCESS
    rows = np.arange(ny)[:, None]
    hmin = np.nanmin(np.where(deeper, np.nan, hw), axis=0)
    has = hmin <= CREST
    band = (np.abs(hw - hmin[None]) < 1e-6) & ~deeper
    crest_row = np.array([rows[band[:, i], 0].mean() if has[i] else np.nan for i in range(nx)])
    have = np.where(has)[0]
    for i in np.where(~has)[0]:
        crest_row[i] = crest_row[have[np.argmin(np.abs(have - i))]]
    seaward = rows > crest_row[None]
    reef = wet & ((seaward & (h <= FOREREEF)) | (~seaward & (h <= BACKREEF)) | (h <= CREST)) & ~deeper
    return ghosts(reef)


def random_field(x, y):
    sigma = SIZE_M / 3.0
    step = sigma / 3.0
    period = float(np.mean(x[:, -1] - x[:, 1]))
    x0 = float(x[0, 1])
    nxa = int(np.ceil(period / step))
    xa = x0 + np.arange(nxa) * (period / nxa)
    ya = np.arange(np.nanmin(y) - 4 * sigma, np.nanmax(y) + 4 * sigma + step, step)
    noise = np.random.default_rng(SEED).standard_normal((ya.size, nxa))
    f = ndimage.gaussian_filter(noise, sigma=(sigma / step, sigma / (period / nxa)), mode=("nearest", "wrap"))
    f = np.concatenate([f, f[:, :1]], axis=1)
    interp = RegularGridInterpolator((ya, np.append(xa, x0 + period)), f)
    return interp(np.stack([y, x0 + np.mod(x - x0, period)], axis=-1))


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "init_reef_patchy.nc"
    with netCDF4.Dataset(HERE / "roms_grid_default_1.nc") as g:
        h, mask, x, y, pm, pn = (np.ma.filled(g[k][:], np.nan).astype(float)
                                 for k in ("h", "mask_rho", "x_rho", "y_rho", "pm", "pn"))
    area = 1.0 / (pm * pn)
    sel = reef_mask(h, mask > 0.5)
    sel[:, [0, -1]] = False
    v, w = random_field(x, y)[sel], area[sel]
    order = np.argsort(-v, kind="stable")
    cum_mid = (np.cumsum(w[order]) - 0.5 * w[order]) / w.sum()
    k = np.searchsorted(np.cumsum(list(COVER.values())), cum_mid, side="right")
    names = list(COVER) + ["bare"]
    labels = np.empty(v.size, dtype=object)
    labels[order] = [names[min(i, len(COVER))] for i in k]
    cls = np.full(h.shape, "bare", dtype=object)
    cls[sel] = labels
    cls = ghosts(cls)
    fields = {f: np.zeros(h.shape) for f in ("density", "diameter", "height")}
    for name, (n, d, ht) in CLASSES.items():
        fields["density"][cls == name] = n
        fields["diameter"][cls == name] = d
        fields["height"][cls == name] = ht
    fields["thickness"] = np.pi / 4 * fields["diameter"]
    shutil.copy(HERE / "init_reef.nc", out)
    with netCDF4.Dataset(out, "r+") as d:
        for f, a in fields.items():
            d[f"plant_{f}"][:] = np.broadcast_to(a, d[f"plant_{f}"].shape)
        d.vegetation_pattern = ("patchy reef: dense 30 %, sparse 30 %, bare 40 % in ~150 m patches over "
                                "backreef, crest and forereef; lagoon, pass and deep water bare")
        d.vegetation_history = "tests/cases/Reef_Ideal_A15_veg/make_patchy_init.py; thickness = pi/4 x diameter"
    a = area[:, 1:-1]
    for name in ("dense", "sparse"):
        frac = a[cls[:, 1:-1] == name].sum() / a[sel[:, 1:-1]].sum()
        print(f"{name}: {frac:.1%} of the reef area")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
