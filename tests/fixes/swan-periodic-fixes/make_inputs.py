"""Write inputs for the standalone SWAN periodic-boundary test.

Usage: python -I make_inputs.py OUT_DIR

A15-like reef (cross-shore profile of the idealized reef case Reef_Ideal_A15
away from its pass, a15_profile.txt,
interpolated to a uniform 20 m grid, 0-2400 m offshore) with one 200 m wide,
10 m deep pass. Waves Hs 1 m, Tp 10 s from 20 deg east of north (oblique, so
lateral boundaries matter). One folder per run:

  <grid>-<rep|norep>-<mid|seam>/swan.in, bathy.bot, output/

grid  tall: 2 km alongshore period (100 x 121 points: more cross-shore than
            alongshore, so several SWAN processes split the grid in y)
      wide: 4 km period (200 x 121: split in x)
rep   COORDINATES CARTESIAN REPeating (periodic in x) or not
mid   pass in the middle of the domain; seam: pass centred on x = 0, i.e.
      across the periodic seam. With working periodic boundaries "seam" is
      "mid" shifted by half a period.

Output goes to a FRAME on the grid points x = 0 .. xlen - dx (the same
points for rep and norep), not to COMPGRID: with REPEATING, SWAN's COMPGRID
frame spread its points over the full period (spacing xlen/(mxc-1)), so its
output was interpolated between grid points and partly flagged as outside
(SWAN item 11 in 1-fixes/swan-periodic-fixes; hsign_compgrid.nc checks it).
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROFILE = np.loadtxt(HERE / "a15_profile.txt")      # y (m), depth (m)
DX = 20.0
YLEN = 2400.0
GRIDS = {"tall": 2000.0, "wide": 4000.0}
PASS_HALF_WIDTH = 100.0
PASS_DEPTH = 10.0

SWAN_IN = """\
PROJECT '' ' '
 'Swan_Periodic_Test {name}'
MODE NONSTATIONARY TWODIMENSIONAL
SET DEPMIN 0.10 INRHOG 1 NAUTICAL
COORDINATES CARTESIAN {rep}
CGRID REGULAR 0. 0. 0. {xlen:.1f} {ylen:.1f} {mxs} {mys} CIRCLE 72 0.04 1.0 20
INPGRID BOTTOM REGULAR 0. 0. 0. {mxs} {mys} {dx:.1f} {dx:.1f}
READINP BOTTOM 1 'bathy.bot' 3 0 FREE
BOUND SHAPESPEC JONSWAP 3.3 PEAK DSPR DEGREES
BOUNDSPEC SIDE NORTH CONSTANT PAR 1.0 10.0 20.0 4.0
GEN3
FRICTION MADSEN 0.05
OFF QUAD
BREAKING CON 1.0 0.73
TRIAD
PROP BSBT
FRAME 'grid' 0. 0. 0. {xlast:.1f} {ylen:.1f} {mxlast} {mys}
BLOCK 'grid' NOHEADER 'output/hsign.nc' LAY 4 HSIGN 1. OUTPUT 20000101.000000 30 MIN
BLOCK 'grid' NOHEADER 'output/dir.nc' LAY 4 DIR 1. OUTPUT 20000101.000000 30 MIN
BLOCK 'grid' NOHEADER 'output/dissip.nc' LAY 4 DISSIP 1. OUTPUT 20000101.000000 30 MIN
BLOCK 'COMPGRID' NOHEADER 'output/hsign_compgrid.nc' LAY 4 HSIGN 1. OUTPUT 20000101.000000 30 MIN
COMPUTE NONSTATIONARY 20000101.000000 60 SEC 20000101.010000
STOP
"""


def profile(y):
    """A15 depth away from the pass, as a function of cross-shore y (m)."""
    return np.interp(y, PROFILE[:, 0], PROFILE[:, 1])


def bathy(xlen, centre):
    """Depth on the input grid (x = 0..xlen inclusive, y = 0..YLEN)."""
    x = np.arange(0.0, xlen + DX / 2, DX)
    y = np.arange(0.0, YLEN + DX / 2, DX)
    h = np.tile(profile(y)[:, None], (1, x.size))
    dist = np.abs(x - centre)
    dist = np.minimum(dist, xlen - dist)        # periodic distance
    in_pass = dist <= PASS_HALF_WIDTH + 1e-6
    h[:, in_pass] = np.maximum(h[:, in_pass], PASS_DEPTH)
    return h


def main():
    out = Path(sys.argv[1])
    for grid, xlen in GRIDS.items():
        mxs, mys = round(xlen / DX), round(YLEN / DX)
        for rep in ("rep", "norep"):
            for where in ("mid", "seam"):
                name = f"{grid}-{rep}-{where}"
                d = out / name
                (d / "output").mkdir(parents=True, exist_ok=True)
                h = bathy(xlen, xlen / 2 if where == "mid" else 0.0)
                np.savetxt(d / "bathy.bot", h, fmt="%.4f")   # row = one y, from y = 0
                (d / "swan.in").write_text(SWAN_IN.format(
                    name=name, rep="REPEATING" if rep == "rep" else "",
                    xlen=xlen, ylen=YLEN, mxs=mxs, mys=mys, dx=DX,
                    xlast=xlen - DX, mxlast=mxs - 1))
    print(f"wrote {len(GRIDS) * 4} run folders in {out}")


if __name__ == "__main__":
    main()
