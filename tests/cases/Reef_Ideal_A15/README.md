# Reef_Ideal_A15: idealized fringing reef with a pass

An idealized reef case (by the repository's author), ported from COAWST v3.7 to
v3.9 and used by the engine's tests. Application flag `REEF_IDEAL_A15`.

## Domain and physics

- ROMS 203 x 111 rho points, 10 levels, 6 km alongshore x 5 km cross-shore;
  east-west periodic. Cross-shore rows are stretched (about 51 m offshore,
  20 m over the reef, 66 m at the far side), so the grid is curvilinear.
- Bathymetry: a 10 m deep lagoon behind a reef crest 0.50 m deep (rows 31-34),
  one 10 m deep pass through the reef, forereef down to 400 m offshore.
- Tide: 0.15 m, 12 h, at the north boundary (`ana_fsobc.h`).
- Waves (SWAN on the ROMS grid, coupled every 600 s): JONSWAP Hs 1 m, Tp 10 s
  from the north (`wavebc_north.txt`), wave-current interaction with the vortex
  force (`WEC_VF`), spectral Stokes drift.
- Temperature and salinity fixed (`TS_FIXED`); vegetation off in the header
  (the variant `Reef_Ideal_A15_veg` turns it on).

## SWAN: periodic, like ROMS

`swan.in` uses `COORDINATES CARTESIAN REPEATING`, waves only on the north
boundary (`BOUNDPAR2 SEGMENT IJ 0 110 201 110`), with the east and west
boundaries commented out. The `CGRID CURVILINEAR 202 110` coordinate file has
one extra column, column 1 shifted by the period. This needs two engine
patches: `2-improvements/swan-periodic-curvilinear.patch` (periodic
curvilinear grids) and the periodic fixes in `1-fixes/swan-periodic-fixes.patch`.
Its many NetCDF outputs need `2-improvements/swan-netcdf-output.patch`.

For A15's original non-periodic SWAN, restore the east and west boundaries
and remove `REPEATING`. With non-periodic SWAN, ROMS's periodic seam gets
mismatched wave forcing (a 58 mm/s jump in the alongshore depth-mean current
at the seam, against 2 mm/s with periodic SWAN, in a 3 h test).

## Files

The `.in` files name each other without paths, so the model runs inside a
copy of this folder. ROMS and SWAN write NetCDF output under `output/`.

| File | What |
|---|---|
| `reef_ideal_a15.h` | cpp options (as in v3.7) |
| `ocean.in`, `coupling.in`, `swan.in` | ROMS, coupler and SWAN inputs (v3.9 keys) |
| `ana_fsobc.h` | v3.9's file plus the A15 tide branch |
| `roms_grid_default_1.nc`, `init_reef.nc` | ROMS grid and initial state |
| `swan_coord_default_1.grd`, `swan_bathy_default_1.bot` | SWAN grid and depth (same points as ROMS) |
| `swan_*.bot` (dens, diam, hght, thck), `vegetation.in` | vegetation inputs (unused with vegetation off) |
| `wavebc_*.txt` | wave boundary conditions |

Changes from the v3.7 files: `ocean.in` with v3.9's YAML `varinfo`, `VEGNAM`
renamed `VEGNAME` and keys new in v3.9 appended; the v3.9 `coupling.in`
template; SWAN `BLOCK` output as NetCDF; `ana_m2obc.h` and the SCRIP weight
file dropped (v3.9's defaults do the same; the SWAN grid is the ROMS grid).
