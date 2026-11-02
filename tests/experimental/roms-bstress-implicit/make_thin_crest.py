"""Make thin-crest variants of the Reef_Ideal_A15 grid (ROMS grid .nc + SWAN .bot).

    python -I make_thin_crest.py CASE_SRC CASE_DST

Copies CASE_SRC to CASE_DST and adds, next to the default grid (crest 0.50 m,
rows 31-34, flank rx0 0.34):
  thin_smooth   crest rows 31-34 at 0.30 m, flanks (rows 29-39) eased so the
                slope factor rx0 stays <= 0.31, as in the default grid
  thin_steep    crest rows 32-33 at 0.30 m, rows 31 and 34 at 0.71 m (rx0 0.41:
                a narrow 2-row crest, like a realistic reef grid that failed)
  steep_050     crest rows 32-33 at 0.50 m, rows 31 and 34 at 1.19 m (rx0 0.41,
                the default depth): steepness alone
Only the reef columns (default h < 0.6 m at row 32) change; the pass is untouched.
"""
import shutil, sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(src, dst)

def variant(name, rowdepth):
    gf = dst / f"roms_grid_{name}.nc"
    shutil.copy(dst / "roms_grid_default_1.nc", gf)
    with Dataset(gf, "a") as g:
        h = g["h"][:]
        reef = h[32] < 0.6
        for j, d in rowdepth.items():
            h[j, reef] = d
        g["h"][:] = h
        if "hraw" in g.variables:
            g["hraw"][0] = h
    b = np.loadtxt(dst / "swan_bathy_default_1.bot")
    w = b < 9000
    b[w] = h[w]
    np.savetxt(dst / f"swan_bathy_{name}.bot", b, fmt="%15.8f")
    rx = np.abs(h[1:] - h[:-1]) / (h[1:] + h[:-1])
    print(f"{name}: rows 28-40 at i=50 {np.round(h[28:41, 50], 2)}; rx0 max {rx.max():.3f} "
          f"(rows 28-40: {rx[28:40].max():.3f})")

variant("thin_smooth", {29: 1.0, 30: 0.55, 31: 0.30, 32: 0.30, 33: 0.30, 34: 0.30,
                        35: 0.55, 36: 1.0, 37: 1.7, 38: 2.8, 39: 4.3})
variant("thin_steep", {31: 0.71, 32: 0.30, 33: 0.30, 34: 0.71})
variant("steep_050", {31: 1.19, 32: 0.50, 33: 0.50, 34: 1.19})
