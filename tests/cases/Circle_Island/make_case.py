"""Input files of the Circle_Island case: a round island with a fringing reef
on a closed (log-polar) O-grid, ROMS + SWAN.

Usage:
  python3 -I make_case.py [OUTDIR]       (default: this folder)

The grid goes round the island in xi (clockwise, periodic, with no gap: the
grid closes on itself) and outwards in eta. Rho column i (1..Lm) is at the
bearing (i - 0.5) * 360/Lm degrees from north, rho row j (0..Mm+1) at the
radius R_B * exp(j * dtheta), dtheta = 2 pi/Lm, so the cells are square
(log-polar grid). Columns 0 and Lm+1 are exact copies of columns Lm and 1.

Lm = 216 is a multiple of SWAN's 36 direction bins: columns 6 apart are 10
degrees (one direction bin) apart, so with forcing the same all around the
island the solution repeats every 6 columns.

Writes:
  circle_grid.nc         ROMS grid (seam, i.e. column 1, starting at north)
  circle_init.nc         ROMS initial state: rest, uniform T/S, the bed
                         properties SSW_BBL reads (as Reef_Ideal_A15)
  swan_coord.grd         SWAN READGRID COORDINATES (ROMS columns 1..Lm+1,
                         the last one column 1 again; rows 0..Mm+1)
  swan_bathy.bot         SWAN READINP BOTTOM (land = 9999)
  *_roll54.*             the same grid with the seam moved 54 columns
                         (90 degrees) clockwise: new column 1 = old column 55
  swan.in                SWAN input: waves from the north on the outer ring;
                         the lines starting "$INWARD " hold the alternative,
                         waves aimed straight inward at every point of the
                         ring (the case's README shows how to switch)
"""
import sys
from pathlib import Path

import netCDF4
import numpy as np

LM, MM, N = 216, 80, 10                # interior columns (around), rows (outwards), levels
R_B = 550.0                            # radius of rho row 0 (m)
R_LAND = 595.0                         # land inside this radius (rows 0-2)
H_LAGOON, H_CREST, H_DEEP = 3.0, 0.8, 50.0
R_CREST = 1150.0                       # radius of the reef crest (m)
W_BACK, L_FORE = 100.0, 1600.0         # back-reef width, fore-reef e-folding length (m)
ROLL = 54                              # columns the seam moves in the *_roll54 files
NDIR = 36                              # SWAN direction bins
WAVES = (1.0, 10.0, 30.0)              # Hs (m), Tp (s), directional spreading (deg)
# vertical grid as Reef_Ideal_A15
THETA_S, THETA_B, HC = 3.0, 2.0, 20.0

DTH = 2 * np.pi / LM


def depth(r):
    """Lagoon 3 m, crest 0.8 m at R_CREST, fore reef deepening to about 50 m."""
    back = H_LAGOON - (H_LAGOON - H_CREST) * np.exp(-((r - R_CREST) / W_BACK) ** 2)
    fore = H_CREST + (H_DEEP - H_CREST) * (1 - np.exp(-(r - R_CREST) / L_FORE))
    return np.where(r <= R_CREST, back, fore)


def periodic(inner, kind):
    """Add the periodic copies to columns 1..Lm (rho/v: 0..Lm+1; u/psi: 0..Lm, 0 = Lm)."""
    if kind in ("rho", "v"):
        return np.concatenate([inner[..., -1:], inner, inner[..., :1]], axis=-1)
    return np.concatenate([inner[..., -1:], inner], axis=-1)


def make_grid():
    """Grid fields as dicts of arrays with their periodic copies; seam at north."""
    i = np.arange(1, LM + 1)
    b_rho = (i - 0.5) * DTH                         # bearing of rho column i (clockwise from north)
    b_u = i * DTH                                   # u file index k (ROMS i = k+1) lies between rho k and k+1
    jr = np.arange(0, MM + 2)
    r_rho = R_B * np.exp(jr * DTH)                  # rho rows 0..Mm+1
    r_v = R_B * np.exp((np.arange(1, MM + 2) - 0.5) * DTH)    # v rows 1..Mm+1 (file 0..Mm)
    pts = {"rho": (r_rho, b_rho), "u": (r_rho, b_u), "v": (r_v, b_rho), "psi": (r_v, b_u)}
    g = {}
    for k, (r, b) in pts.items():
        R, B = np.meshgrid(r, b, indexing="ij")
        g[f"x_{k}"] = periodic(R * np.sin(B), k)
        g[f"y_{k}"] = periodic(R * np.cos(B), k)
    R, B = np.meshgrid(r_rho, b_rho, indexing="ij")
    ones = np.ones_like(R)
    g["pm"] = periodic(1.0 / (R * DTH), "rho")
    g["pn"] = periodic(1.0 / (R * 2 * np.sinh(DTH / 2)), "rho")
    dm = R * DTH                                    # 1/pm
    dmde = np.zeros_like(R)
    dmde[1:-1] = 0.5 * (dm[2:] - dm[:-2])
    dmde[0], dmde[-1] = dm[1] - dm[0], dm[-1] - dm[-2]
    g["dmde"] = periodic(dmde, "rho")
    g["dndx"] = periodic(0 * ones, "rho")
    # xi points clockwise: its angle from east, counterclockwise, is -bearing
    g["angle"] = periodic(np.angle(np.exp(-1j * B)), "rho")
    g["f"] = periodic(0 * ones, "rho")
    g["h"] = periodic(np.where(R >= R_LAND, depth(R), H_LAGOON), "rho")
    m = periodic((R >= R_LAND).astype(float), "rho")
    g["mask_rho"] = m
    g["mask_u"] = m[:, :-1] * m[:, 1:]
    g["mask_v"] = m[:-1, :] * m[1:, :]
    g["mask_psi"] = g["mask_u"][:-1, :] * g["mask_u"][1:, :]
    return g


def roll(g, K):
    """The same grid with the seam K columns further clockwise (new 1 = old 1+K)."""
    out = {}
    for k, a in g.items():
        kind = "rho" if a.shape[1] == LM + 2 else "u"
        out[k] = periodic(np.roll(a[:, 1:LM + 1], -K, axis=1), kind)
    # the u/psi copy (file index 0 = Lm) and the rho/v copies are exact by construction
    return out


def write_grid(g, path, note):
    with netCDF4.Dataset(path, "w", format="NETCDF4_CLASSIC") as d:
        d.type = "ROMS GRID file"
        d.title = "Circle_Island: round island with a fringing reef, closed log-polar O-grid"
        d.history = f"tests/cases/Circle_Island/make_case.py; {note}"
        for name, size in (("xi_rho", LM + 2), ("eta_rho", MM + 2), ("xi_u", LM + 1), ("eta_u", MM + 2),
                           ("xi_v", LM + 2), ("eta_v", MM + 1), ("xi_psi", LM + 1), ("eta_psi", MM + 1),
                           ("one", 1)):
            d.createDimension(name, size)
        v = d.createVariable("spherical", "S1", ("one",))
        v[:] = np.array([b"F"])
        r_out = R_B * np.exp((MM + 1.5) * DTH)
        r_in = R_B * np.exp(0.5 * DTH)
        for name, val in (("xl", 2 * np.pi * r_out), ("el", r_out - r_in)):
            v = d.createVariable(name, "f8", ("one",))
            v.units = "meter"
            v[:] = val
        dims = {"rho": ("eta_rho", "xi_rho"), "u": ("eta_u", "xi_u"), "v": ("eta_v", "xi_v"),
                "psi": ("eta_psi", "xi_psi")}
        units = {"pm": "meter-1", "pn": "meter-1", "dmde": "meter", "dndx": "meter",
                 "angle": "radians", "f": "second-1", "h": "meter"}
        for name, a in g.items():
            kind = name.split("_")[-1] if name.startswith(("x_", "y_", "mask_")) else "rho"
            v = d.createVariable(name, "f8", dims[kind], zlib=True)
            if name in units:
                v.units = units[name]
            elif name.startswith(("x_", "y_")):
                v.units = "meter"
            v[:] = a


def write_swan(g, outdir, suffix):
    x, y, h, m = g["x_rho"], g["y_rho"], g["h"], g["mask_rho"]
    cols = slice(1, LM + 2)                         # ROMS columns 1..Lm+1 (Lm+1 = 1)
    with open(outdir / f"swan_coord{suffix}.grd", "w") as f:
        for a in (x[:, cols], y[:, cols]):
            for row in a:
                f.write(" ".join(f"{v:.4f}" for v in row) + "\n")
    with open(outdir / f"swan_bathy{suffix}.bot", "w") as f:
        for row in np.where(m[:, cols] > 0.5, h[:, cols], 9999.0):
            f.write(" ".join(f"{v:.4f}" for v in row) + "\n")


def stretching4(s):
    c = (1 - np.cosh(THETA_S * s)) / (np.cosh(THETA_S) - 1)
    return (np.exp(THETA_B * c) - 1) / (1 - np.exp(-THETA_B))


def write_init(path):
    sc_w = np.linspace(-1, 0, N + 1)
    sc_r = (np.arange(1, N + 1) - N - 0.5) / N
    Lp, Mp = LM + 2, MM + 2
    with netCDF4.Dataset(path, "w", format="NETCDF4_CLASSIC") as d:
        d.type = "ROMS initial file"
        d.title = "Circle_Island: rest, uniform T/S, bed properties as Reef_Ideal_A15"
        d.history = "tests/cases/Circle_Island/make_case.py"
        for name, size in (("xi_rho", Lp), ("eta_rho", Mp), ("xi_u", Lp - 1), ("eta_u", Mp),
                           ("xi_v", Lp), ("eta_v", Mp - 1), ("s_rho", N), ("s_w", N + 1),
                           ("ocean_time", 1)):
            d.createDimension(name, size)

        def var(name, dims, value, units=None, dtype="f8"):
            v = d.createVariable(name, dtype, dims, zlib=True)
            if units:
                v.units = units
            v[:] = value
        var("spherical", (), 0, dtype="i4")
        var("Vtransform", (), 2, dtype="i4")
        var("Vstretching", (), 4, dtype="i4")
        var("theta_s", (), THETA_S)
        var("theta_b", (), THETA_B)
        var("Tcline", (), HC, "meter")
        var("hc", (), HC, "meter")
        var("s_rho", ("s_rho",), sc_r)
        var("s_w", ("s_w",), sc_w)
        var("Cs_r", ("s_rho",), stretching4(sc_r))
        var("Cs_w", ("s_w",), stretching4(sc_w))
        var("ocean_time", ("ocean_time",), 0.0, "seconds since 2000-01-01 00:00:00")
        t, r2, u2, v2 = ("ocean_time",), ("eta_rho", "xi_rho"), ("eta_u", "xi_u"), ("eta_v", "xi_v")
        var("zeta", t + r2, 0.0, "meter")
        var("ubar", t + u2, 0.0, "meter second-1")
        var("vbar", t + v2, 0.0, "meter second-1")
        var("u", t + ("s_rho",) + u2, 0.0, "meter second-1")
        var("v", t + ("s_rho",) + v2, 0.0, "meter second-1")
        var("temp", t + ("s_rho",) + r2, 27.0, "Celsius")
        var("salt", t + ("s_rho",) + r2, 36.0, "1")
        var("grain_diameter", t + r2, 0.12, "meter")
        var("grain_density", t + r2, 2650.0, "kilogram meter-3")
        var("settling_vel", t + r2, 0.15, "meter second-1")
        var("erosion_stress", t + r2, 0.2, "meter2 second-2")


SWAN_IN = """PROJECT '' ' '
 'Circle_Island'
 'Round island with a fringing reef, closed log-polar O-grid'
 'tests/cases/Circle_Island/make_case.py'
MODE NONSTATIONARY TWODIMENSIONAL
SET DEPMIN 0.10 INRHOG 1 NAUTICAL
$ The grid goes round the island and closes on itself (the coordinate file's
$ last column is column 1 again): REPEATING with a zero period, which needs
$ the engine's swan-periodic-curvilinear and swan-closed-ring patches.
COORDINATES CARTESIAN REPEATING
NSGRIDS 1
$ SWAN column k = ROMS column k (k = 1..{lm}), rows = ROMS rows 0..{mm1}
CGRID CURVILINEAR {lm} {mm1} EXC 9.999000e+003 &
        CIRCLE {ndir} 0.04 1.0 20
READGRID COORDINATES 1 'swan_coord.grd' 4 0 0 FREE
INPGRID BOTTOM CURVILINEAR 0 0 {lm} {mm1} EXC 9.999000e+003
READINP BOTTOM  1 'swan_bathy.bot' 4 0 FREE
INPGRID CURRENT CURVILINEAR 0 0 {lm} {mm1} EXC 9.999000e+003 &
        NONSTAT  20000101.000000 25 DAY 20000126.000000
INPGRID WLEV CURVILINEAR 0 0 {lm} {mm1} EXC 9.999000e+003 &
        NONSTAT  20000101.000000 25 DAY 20000126.000000
INPGRID FRIC CURVILINEAR 0 0 {lm} {mm1} EXC 9.999000e+003 &
        NONSTAT  20000101.000000 25 DAY 20000126.000000
$ Waves on the whole outer ring (row {mm1}); SWAN uses only the part of the
$ spectrum that travels into the domain. Hs (m), Tp (s), direction (deg,
$ nautical: coming from), directional spreading (deg).
BOUND SHAPESPEC JONSWAP 3.3 PEAK DSPR DEGREES
BOUNDSPEC SEGMENT IJ 0 {mm1} {lm1} {mm1} CONSTANT PAR {hs} {tp} 0. {dspr}
$ Alternative: waves aimed straight inward at every point of the ring, the
$ same all around the island. Remove the INWARD prefixes and comment out
$ the BOUNDSPEC line above (README).
{inward}
BLOCK 'COMPGRID' NOHEADER 'output/xp.nc'  LAY 4 XP 1.
BLOCK 'COMPGRID' NOHEADER 'output/yp.nc'  LAY 4 YP 1.
BLOCK 'COMPGRID' NOHEADER 'output/depth.nc'  LAY 4 DEPTH 1.
BLOCK 'COMPGRID' NOHEADER 'output/vel.nc'  LAY 4 VEL 1.
BLOCK 'COMPGRID' NOHEADER 'output/watlev.nc'  LAY 4 WATLEV 1.
BLOCK 'COMPGRID' NOHEADER 'output/hsign.nc'  LAY 4 HSIGN 1.
BLOCK 'COMPGRID' NOHEADER 'output/dir.nc'  LAY 4 DIR 1.
BLOCK 'COMPGRID' NOHEADER 'output/tm01.nc'  LAY 4 TM01 1.
BLOCK 'COMPGRID' NOHEADER 'output/wlen.nc'  LAY 4 WLEN 1.
BLOCK 'COMPGRID' NOHEADER 'output/ubot.nc'  LAY 4 UBOT 1.
BLOCK 'COMPGRID' NOHEADER 'output/dissip.nc'  LAY 4 DISSIP 1.
$ Physics and numerics as Reef_Ideal_A15
GEN3
FRICTION MADSEN 0.3
OFF QUAD
BREAKING CON 1.0 0.73
PROP BSBT
TRIAD
COMPUTE NONSTATIONARY 20000101.000000 60 SEC 20000101.010000
RESTART 'output/swan_rst.dat' FREE 1 HR
STOP
"""


def inward_block(g):
    """BOUNDSPEC ... VARIABLE PAR at every point of the outer ring, each aimed
    along its own spoke, all lines prefixed "$INWARD " (inactive)."""
    x = g["x_rho"][-1, 1:LM + 1].astype(np.float32).astype(float)    # as SWAN stores them
    y = g["y_rho"][-1, 1:LM + 1].astype(np.float32).astype(float)
    dist = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    hs, tp, dspr = WAVES
    lines = [f"BOUNDSPEC SEGMENT IJ 0 {MM + 1} {LM - 1} {MM + 1} VARIABLE PAR &"]
    for c in range(LM):
        bearing = (c + 0.5) * 360.0 / LM           # outward spoke of SWAN column c+1 = coming from
        end = " &" if c < LM - 1 else ""
        lines.append(f"   {dist[c]:.4f} {hs} {tp} {bearing:.6f} {dspr}{end}")
    return "\n".join("$INWARD " + s for s in lines)


def courant(g, dt_fast):
    wet = g["mask_rho"] > 0
    c = np.sqrt(9.81 * g["h"]) * dt_fast * np.sqrt(g["pm"] ** 2 + g["pn"] ** 2)
    return c[wet].max()


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    out.mkdir(parents=True, exist_ok=True)
    g = make_grid()
    for a in g.values():
        if a.shape[1] == LM + 2:
            assert np.array_equal(a[:, 0], a[:, LM]) and np.array_equal(a[:, LM + 1], a[:, 1])
        else:
            assert np.array_equal(a[:, 0], a[:, LM])
    gr = roll(g, ROLL)
    write_grid(g, out / "circle_grid.nc", "seam (column 1) starting at north")
    write_grid(gr, out / f"circle_grid_roll{ROLL}.nc", f"seam moved {ROLL} columns clockwise (to east)")
    write_swan(g, out, "")
    write_swan(gr, out, f"_roll{ROLL}")
    write_init(out / "circle_init.nc")
    hs, tp, dspr = WAVES
    (out / "swan.in").write_text(SWAN_IN.format(
        lm=LM, mm1=MM + 1, lm1=LM - 1, ndir=NDIR, hs=hs, tp=tp, dspr=dspr, inward=inward_block(g)))
    r = R_B * np.exp(np.arange(MM + 2) * DTH)
    wet = r >= R_LAND
    dx = r * DTH
    print(f"Circle_Island: Lm {LM}, Mm {MM}; radius {r[wet][0]:.0f}-{r[-1]:.0f} m, "
          f"cells {dx[wet][0]:.1f}-{dx[-1]:.1f} m; depth {depth(r[wet]).min():.2f}-{depth(r[-1]):.1f} m; "
          f"barotropic Courant {courant(g, 4.0 / 10):.2f} at DT 4 s, NDTFAST 10")


if __name__ == "__main__":
    main()
