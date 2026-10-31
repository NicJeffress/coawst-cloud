# Test: swan-output-fixes

Checks [`1-fixes/swan-output-fixes.patch`](../../../build/coawst/patches/1-fixes/swan-output-fixes.md):
SWAN must write its output at the right locations, with the same coordinates
for any number of processes, and without randomly missing values.

## The idea

Ask SWAN for exactly the kinds of output that go wrong, run with 1 and with 2
processes, and check the files.

## What it does, step by step

1. Builds stock **Inlet_test** with the patch series before this patch
   (`coawst-test:swanout-before`) and with it (`-after`).
2. Adds to `swan.in` 9 output points that lie between grid points, around
   (5070 m, 10070 m), and two tables for them:
   `TABLE 'pts' ... 'pts.table'` (text) and `TABLE 'pts' ... 'pts.nc'`
   (NetCDF), every 10 min. The case already writes `hsig.nc` with
   `BLOCK 'COMPGRID'`.
3. Sets `MALLOC_PERTURB_=85`: glibc then fills new memory with a non-zero
   pattern, so the never-initialised obstacle flags read "true" in every run
   (without it they read "true" at random, so the test could pass by luck).
4. Runs each image for 1 h with 1 SWAN process and with 2 (`before-1swan`,
   `before-2swan`, `after-1swan`, `after-2swan`).
5. `check.py` checks each run pair:

   | Change | Check |
   |---|---|
   | `table_nc_coordinates` | x, y in `pts.nc` (2 SWAN) equal the 9 points' coordinates |
   | `compgrid_nc_coordinates` | x in `hsig.nc` (1 SWAN) has no -1e10 values |
   | `output_obstacle_flags` | no -9 (missing) Hs values in `pts.table`, 1 and 2 SWAN |

   PASS needs at least one BAD before the patch and all ok after.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/swan-output-fixes/run.sh OUTDIR
```

About 20 min on 4 vCPUs.

## Reading the output

One line per check with the numbers it found and ok/BAD, e.g.

```
table_nc_coordinates     TABLE .nc, 2 SWAN: point coordinates   x[0..2] = 0, 200, 400        BAD
```

means the first three table points were written at x = 0, 200, 400 m (the
grid's first cells) instead of 4930, 5070, 5210 m.

## Last result

2026-10-30, control VM: PASS (before: three BAD; after: all ok).
