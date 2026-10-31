# Test: roms-sed-morph-tiling

Checks [`1-fixes/roms-sed-morph-tiling.patch`](../../../build/coawst/patches/1-fixes/roms-sed-morph-tiling.md):
with sediment morphology, ROMS's results must not depend on how the grid is
split between processors.

## The idea

A correct parallel model gives bit-for-bit the same answer on any number of
processors. So run the same case twice, once with ROMS on one tile (1x1) and
once on two (1x2), and compare. Before the patch they differ near the tile
edge; after it they must be identical to the last bit.

## What it does, step by step

1. Builds two images of COAWST's stock **Inlet_test** (a tidal inlet with
   waves, suspended sand and bedload, `SED_MORPH` on): one with the patch
   series before this patch (`coawst-test:sedtile-before`), one with it
   (`-after`).
2. Runs each for 6 simulated hours (argument `HOURS`), with 1 SWAN process and
   ROMS on 1x1 and on 1x2 tiles: four runs, `before_1x1`, `before_1x2`,
   `after_1x1`, `after_1x2`. The 1x2 split puts the tile edge across the
   inlet, where sand moves; 6 h is enough for all three bugs (the last one
   first shows after 3.4 h).
3. Compares, with `tests/tools/compare_nc.py`, the variables `bath`, `zeta`,
   `ubar`, `vbar`, `u`, `v`, `bed_thickness`:
   - before: 1x1 vs 1x2 at the last record: must differ;
   - after: 1x1 vs 1x2: must be bit-identical;
   - 1x1 before vs 1x1 after, every record: must be bit-identical (on one tile
     there are no tile edges, so the patch must not change anything).

`plot_tiling.py OUTDIR FIGURE.png` maps the difference and plots it against
time.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-sed-morph-tiling/run.sh OUTDIR [HOURS]
```

About 40 min on 4 vCPUs. Needs Docker and Python with numpy and netCDF4.

## Reading the output

`compare_nc.py` prints, per variable, the largest absolute difference, the
largest value (for scale), where the difference is, and whether the two are
bit-identical:

```
== before the patch: ROMS 1x1 vs 1x2, last record
variable                    max |A-B|      max |A|  at (index)       identical
bath                         0.006503        15.52  (36, 33)         NO
...
== after the patch: ROMS 1x1 vs 1x2, last record
bath                                0        15.52  ()               yes
...
PASS
```

The index `(36, 33)` is (row, column): row 36 is next to the tile edge.

## Last result

2026-10-30, control VM: PASS. Before: 6.5 mm bathymetry difference at 6 h;
after: bit-identical. Details in the patch document.
