# Circle_Island: a round island on a closed O-grid

An idealized coupled case (ROMS + SWAN) made for the engine's tests of grids
that go round an island and close on themselves. Application flag
`CIRCLE_ISLAND`. All input files are written by `make_case.py`.

## Domain

- **Grid**: log-polar O-grid, 216 columns round the island (xi, clockwise,
  periodic with no gap: column 217 is column 1 again) and 80 interior rings
  outwards (eta). Rho column i is at the bearing (i - 0.5) x 1.667 degrees
  from north, ring j at the radius 550 m x exp(j x 2 pi/216), so the cells
  are square: 17.5 m at the shore (radius 600 m) to 169 m at the outer edge
  (radius 5.8 km). 10 levels, as Reef_Ideal_A15.
- **Seam**: the boundary between column 216 and column 1, at north.
  `*_roll54.*` hold the same domain numbered from 90 degrees further on
  (seam at east), to check that results do not depend on where the seam is.
- **Bathymetry** (the same at every bearing): land inside 595 m (rings 0-2),
  a 3 m deep lagoon, a reef crest 0.8 m deep at 1150 m, then a fore reef
  deepening to 47 m at the outer edge.
- **Boundaries**: the island side (ROMS south) is closed; the outer ring (ROMS
  north) is open with a 0.15 m, 12 h tide, the same all round
  (`ana_fsobc.h`), and SWAN's wave boundary.
- **Waves** (`swan.in`, 36 directions, so 6 columns = one direction bin):
  JONSWAP Hs 1 m, Tp 10 s, 30 degree spreading, from the north. The lines
  starting `$INWARD ` hold the alternative: at every point of the outer ring
  the same waves aimed straight inward, so forcing and depth are the same
  all round the island and the solution must repeat every 6 columns.
- **Physics**: as Reef_Ideal_A15 (vortex-force wave-current interaction, GLS
  mixing, SSW bottom boundary layer, T and S fixed), with `CURVGRID` and the
  Coriolis parameter 0. ROMS DT 4 s, NDTFAST 10 (barotropic Courant 0.18);
  SWAN step 60 s; coupling every 600 s.
- **Start date**: the initial file's time is 2000-01-01 ("seconds since
  2000-01-01"), and `ocean.in` has `DSTART = 730119` days, the same date
  counted from year 0 (`TIME_REF = 0`). With `DSTART = 0` ROMS's step
  counter overflows (time - DSTART is about 1.6e10 steps) and ends up at 1;
  a fresh run does not notice, but a restarted run then starts its time
  stepping cold (Euler instead of AB3) and is not exact.

## Needs

`COORDINATES CARTESIAN REPEATING` on a curvilinear grid that closes on
itself: the engine patches `2-improvements/swan-periodic-curvilinear` and
`2-improvements/swan-closed-ring`. Without the second, SWAN stops with
"REPeating curvilinear grid: no period found".

## Variants (sed scripts for `tests/tools/case_inside.sh`)

| Variant | OCEANSED | SWANSED |
|---|---|---|
| seam at east | `s/circle_grid\.nc/circle_grid_roll54.nc/` | `s/swan_coord\.grd/swan_coord_roll54.grd/; s/swan_bathy\.bot/swan_bathy_roll54.bot/` |
| waves from all sides | | `s/^\$INWARD //; s/^(BOUNDSPEC SEGMENT IJ [0-9 ]+ CONSTANT .*)/$ \1/` |

## Files

| File | What |
|---|---|
| `make_case.py` | writes every file below (`python3 -I make_case.py [OUTDIR]`) |
| `circle_island.h` | cpp options |
| `ocean.in`, `coupling.in` | ROMS and coupler inputs (from Reef_Ideal_A15's) |
| `swan.in` | SWAN input (written by `make_case.py`) |
| `ana_fsobc.h` | v3.9's file plus the Circle_Island tide branch |
| `circle_grid.nc`, `circle_grid_roll54.nc` | ROMS grid, seam at north / east |
| `circle_init.nc` | ROMS initial state: rest, 27 C, 36, bed properties |
| `swan_coord*.grd`, `swan_bathy*.bot` | SWAN grid and depth (ROMS columns 1..217, rows 0..81) |
