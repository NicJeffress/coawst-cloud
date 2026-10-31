"""Inputs for the test of 2-improvements/swan-periodic-curvilinear.patch.

Usage: python -I make_inputs.py OUT_DIR

Same reef, pass and waves as tests/fixes/swan-periodic-fixes/make_inputs.py (A15 cross-shore profile, one
200 m wide, 10 m deep pass, Hs 1 m, Tp 10 s from 20 deg east of north), on
curvilinear grids with COORDINATES CARTESIAN REPEATING. The coordinate file
has one column more than the periodic grid: column 1 shifted by one period.
One folder per run, <case>/swan.in, coord.grd, bathy.bot, output/:

  uni-reg-mid   regular grid, 2 km period, uniform 20 m (100 x 121 points),
                as `tall-rep-mid` but with the boundary given as SEGMENT IJ
                (BOUNDSPEC SIDE is not allowed on curvilinear grids)
  uni-crv-mid   the same grid as a curvilinear grid: must reproduce
                uni-reg-mid
  uni-reg-flat  regular, no pass, with FORCE output: the solution must be
                the same in every column, also at the seam
  str-mid       grid stretched in both directions, like Reef_Ideal_A15:
                alongshore 20 m at the pass to 40 m at the sides (3 km
                period, 100 columns), cross-shore A15's own rows (51 m at
                the south wall, 20 m at the crest, 66 m at 2.4 km)
  str-seam      the str-mid grid and reef rolled by half a period, so the
                seam runs through the pass and the fine 20 m columns; must
                equal str-mid rolled back
  str-flat      stretched, no pass, with FORCE output: same in every column
  str-norep     str-mid without REPEATING (lateral boundaries)
  str-badper    str-mid with a coordinate file whose last column is not
                column 1 shifted by one period: SWAN must stop with an error
  a15-mid       Reef_Ideal_A15's own SWAN grid and bathymetry (202 x 111
                points, 6061 m period; its coordinate file already has the
                closing column), with these oblique waves
  a15-seam      the same rolled by half a period: seam through the pass
  a15-norep     a15-mid without REPEATING

  str-search    str-mid plus output on a FRAME over two periods (x = -L/2
                .. 3L/2) and at POINTS inside the mesh across the seam and
                whole periods away, to test the search for output locations
                (CVMESH). One process only: merging FRAME output from several
                processes fails on any curvilinear grid (a SWAN bug, not
                fixed; see the patch document).
"""
import sys
from pathlib import Path

import netCDF4
import numpy as np

HERE = Path(__file__).resolve().parent
A15_DIR = HERE.parents[1] / "cases" / "Reef_Ideal_A15"
A15_GRID = A15_DIR / "roms_grid_default_1.nc"
PASS_HALF_WIDTH = 100.0
PASS_DEPTH = 10.0
YMAX = 2400.0

SWAN_IN = """\
PROJECT '' ' '
 'Swan_Periodic_Test {name}'
MODE NONSTATIONARY TWODIMENSIONAL
SET DEPMIN 0.10 INRHOG 1 NAUTICAL
COORDINATES CARTESIAN {rep}
{grid}
BOUND SHAPESPEC JONSWAP 3.3 PEAK DSPR DEGREES
BOUNDSPEC SEGMENT IJ 0 {mys} {ilast} {mys} CONSTANT PAR 1.0 10.0 20.0 4.0
GEN3
FRICTION MADSEN 0.05
OFF QUAD
BREAKING CON 1.0 0.73
TRIAD
PROP BSBT
BLOCK 'COMPGRID' NOHEADER 'output/hsign.nc' LAY 4 HSIGN 1. OUTPUT 20000101.000000 30 MIN
BLOCK 'COMPGRID' NOHEADER 'output/dir.nc' LAY 4 DIR 1. OUTPUT 20000101.000000 30 MIN
BLOCK 'COMPGRID' NOHEADER 'output/dissip.nc' LAY 4 DISSIP 1. OUTPUT 20000101.000000 30 MIN
{extra}COMPUTE NONSTATIONARY 20000101.000000 60 SEC 20000101.010000
STOP
"""
REG_GRID = """\
CGRID REGULAR 0. 0. 0. {xlen:.1f} {ylen:.1f} {mxs} {mys} CIRCLE 72 0.04 1.0 20
INPGRID BOTTOM REGULAR 0. 0. 0. {mxs} {mys} {dx:.1f} {dy:.1f}
READINP BOTTOM 1 'bathy.bot' 3 0 FREE"""
CRV_GRID = """\
CGRID CURVILINEAR {mxs} {mys} CIRCLE 72 0.04 1.0 20
READGRID COORDINATES 1 'coord.grd' 3 0 0 FREE
INPGRID BOTTOM CURVILINEAR 0 0 {mxs} {mys}
READINP BOTTOM 1 'bathy.bot' 3 0 FREE"""
A15_CRV_GRID = """\
CGRID CURVILINEAR {mxs} {mys} EXC 9.999000e+003 CIRCLE 72 0.04 1.0 20
READGRID COORDINATES 1 'coord.grd' 3 0 0 FREE
INPGRID BOTTOM CURVILINEAR 0 0 {mxs} {mys} EXC 9.999000e+003
READINP BOTTOM 1 'bathy.bot' 3 0 FREE"""
FORCE_OUT = """\
BLOCK 'COMPGRID' NOHEADER 'output/force.nc' LAY 4 FORCE 1. OUTPUT 20000101.000000 30 MIN
"""
SEARCH_OUT = """\
FRAME 'frm' {fx0:.3f} {fy0:.3f} 0. {flen:.3f} {fylen:.3f} {fmx} {fmy}
BLOCK 'frm' NOHEADER 'output/hsign_frm.nc' LAY 4 HSIGN 1. OUTPUT 20000101.010000 1 HR
POINTS 'pts' FILE 'points.txt'
TABLE 'pts' NOHEADER 'output/pts.tab' XP YP HSIGN OUTPUT 20000101.010000 1 HR
"""


def a15_profile():
    """A15 cross-shore rows (y <= YMAX) and depth away from the pass."""
    with netCDF4.Dataset(A15_GRID) as d:
        y = d["y_rho"][:, 30].filled()
        h = d["h"][:, 30].filled()
    keep = y <= YMAX
    return y[keep], h[keep]


def depth(x, y, period, centre, yrows, hrows):
    """Depth at nodes (x, y) (2-D arrays): profile plus the pass at
    `centre` (None: no pass), with periodic distance along x."""
    h = np.interp(y, yrows, hrows)
    if centre is not None:
        dist = np.abs(x - centre) % period
        dist = np.minimum(dist, period - dist)
        in_pass = dist <= PASS_HALF_WIDTH + 1e-6
        h[in_pass] = np.maximum(h[in_pass], PASS_DEPTH)
    return h


def stretched_x(n, period, fine_at):
    """n+1 alongshore positions over one period plus the closing node:
    spacing 2/3*ds at `fine_at` to 4/3*ds half a period away (20 to 40 m
    for ds = 30 m), smooth and periodic: x(s + period) = x(s) + period."""
    s = np.arange(n + 1) * (period / n)
    c = 1.0 / 3.0
    return s - c * period / (2 * np.pi) * np.sin(2 * np.pi * (s - fine_at) / period)


def write_case(out, name, *, x, y, h, rep, curv, extra="", coord=None, template=CRV_GRID):
    """x, y: node coordinates (ny, nx+1) including the closing column."""
    d = out / name
    (d / "output").mkdir(parents=True, exist_ok=True)
    mys, mxs = y.shape[0] - 1, x.shape[1] - 1
    if curv:
        grid = template.format(mxs=mxs, mys=mys)
        cx, cy = coord if coord is not None else (x, y)
        with open(d / "coord.grd", "w") as f:
            np.savetxt(f, cx, fmt="%.6f")     # all x (row = one y, from the south)
            np.savetxt(f, cy, fmt="%.6f")     # then all y
    else:
        dx, dy = x[0, 1] - x[0, 0], y[1, 0] - y[0, 0]
        grid = REG_GRID.format(xlen=x[0, -1] - x[0, 0], ylen=y[-1, 0] - y[0, 0],
                               mxs=mxs, mys=mys, dx=dx, dy=dy)
    np.savetxt(d / "bathy.bot", h, fmt="%.4f")             # 9999: land (A15)
    # periodic: the boundary row has mxs points (indices 0..mxs-1)
    (d / "swan.in").write_text(SWAN_IN.format(
        name=name, rep="REPEATING" if rep else "", grid=grid, mys=mys,
        ilast=mxs - 1 if rep else mxs, extra=extra))
    return d


def main():
    out = Path(sys.argv[1])
    yrows, hrows = a15_profile()

    # uniform 20 m grid, 2 km period (as `tall` in make_inputs.py)
    period = 2000.0
    xu, yu = np.meshgrid(np.arange(0.0, period + 10, 20.0), np.arange(0.0, YMAX + 10, 20.0))
    hu = depth(xu, yu, period, period / 2, yrows, hrows)
    write_case(out, "uni-reg-mid", x=xu, y=yu, h=hu, rep=True, curv=False)
    write_case(out, "uni-crv-mid", x=xu, y=yu, h=hu, rep=True, curv=True)
    write_case(out, "uni-reg-flat", x=xu, y=yu, h=depth(xu, yu, period, None, yrows, hrows),
               rep=True, curv=False, extra=FORCE_OUT)

    # stretched both ways, 3 km period, 100 columns
    period, n = 3000.0, 100
    xs_mid = stretched_x(n, period, fine_at=period / 2)
    xs_seam = stretched_x(n, period, fine_at=0.0)
    xm, ym = np.meshgrid(xs_mid, yrows)
    xe, ye = np.meshgrid(xs_seam, yrows)
    hm = depth(xm, ym, period, period / 2, yrows, hrows)
    he = depth(xe, ye, period, 0.0, yrows, hrows)

    # output search: a frame over two periods, and points across the seam
    # (between the last column and column 1 + period) and a period away
    ny = yrows.size
    fy0, fy1 = yrows[2], yrows[ny - 3]
    search = SEARCH_OUT.format(fx0=-period / 2, fy0=fy0, flen=2 * period, fylen=fy1 - fy0,
                               fmx=4 * n, fmy=21)
    jrow = ny // 2                       # a row near the crest
    xl, x1 = xs_mid[n - 1], xs_mid[n]    # last column, column 1 + period
    yy = yrows[jrow]
    pts = [(xl + 0.25 * (x1 - xl), yy), (xl + 0.5 * (x1 - xl), yy), (xl + 0.75 * (x1 - xl), yy),
           (xs_mid[0] - 0.5 * (x1 - xl), yy),              # same as the 0.5 point
           (xs_mid[10] + period, yy), (xs_mid[10] - period, yy),   # = column 11
           (xs_mid[10], yy), (xs_mid[10] + 2 * period, yy),
           (xl + 0.5 * (x1 - xl), 0.5 * (yrows[jrow] + yrows[jrow + 1]))]
    write_case(out, "str-mid", x=xm, y=ym, h=hm, rep=True, curv=True)
    d = write_case(out, "str-search", x=xm, y=ym, h=hm, rep=True, curv=True, extra=search)
    np.savetxt(d / "points.txt", np.array(pts), fmt="%.6f")

    write_case(out, "str-seam", x=xe, y=ye, h=he, rep=True, curv=True)
    write_case(out, "str-flat", x=xm, y=ym, h=depth(xm, ym, period, None, yrows, hrows),
               rep=True, curv=True, extra=FORCE_OUT)
    write_case(out, "str-norep", x=xm, y=ym, h=hm, rep=False, curv=True)
    bad = xm.copy()
    bad[5:, -1] += 30.0                  # closing column off by a whole mesh
    write_case(out, "str-badper", x=xm, y=ym, h=hm, rep=True, curv=True, coord=(bad, ym))

    # Reef_Ideal_A15's SWAN grid (= ROMS rho grid incl. boundary points),
    # rolled by half a period for the seam case
    c = np.loadtxt(A15_DIR / "swan_coord_default_1.grd")
    ha = np.loadtxt(A15_DIR / "swan_bathy_default_1.bot")
    ny, nx = ha.shape                    # 111 x 203: 202 periodic columns + closing one
    xa, ya = c[:nx * ny].reshape(ny, nx), c[nx * ny:].reshape(ny, nx)
    per = xa[0, -1] - xa[0, 0]
    k = (nx - 1) // 2                    # roll by 101 of the 202 columns
    idx = (np.arange(nx) + k) % (nx - 1)
    shift = np.where(np.arange(nx) + k >= nx - 1, per, 0.0)
    xr, yr, hr = xa[:, idx] + shift, ya[:, idx], ha[:, idx]
    for name, x_, y_, h_, rep in (("a15-mid", xa, ya, ha, True), ("a15-seam", xr, yr, hr, True),
                                  ("a15-norep", xa, ya, ha, False)):
        write_case(out, name, x=x_, y=y_, h=h_, rep=rep, curv=True, template=A15_CRV_GRID)
    print(f"wrote {sum(1 for p in out.iterdir() if p.is_dir())} run folders in {out}")


if __name__ == "__main__":
    main()
