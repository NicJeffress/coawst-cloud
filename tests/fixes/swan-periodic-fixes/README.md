# Test: swan-periodic-fixes

Checks [`1-fixes/swan-periodic-fixes.patch`](../../../build/coawst/patches/1-fixes/swan-periodic-fixes.md):
SWAN with periodic lateral boundaries (`COORDINATES ... REPEATING`). Two
scripts:

- `run.sh`: source check and standalone SWAN runs (`periodic_compgrid_frame`,
  `periodic_y_strips`, `periodic_coupled_stokes` in the source);
- `run_a15_coupled.sh`: coupled ROMS + SWAN on the idealized reef
  (`periodic_coupled_stokes` in a run).

## The idea

A periodic grid has no east and west boundaries: what leaves on one side
comes back on the other. Two properties then must hold, and are cheap to
check: output on the grid points must be the grid's own values (nothing
interpolated, nothing missing), and the answer must not depend on how many
processes SWAN runs on. A coupled run then checks that the waves SWAN hands
to ROMS across the seam are the right ones.

## run.sh, step by step

1. **Source check** (`check_source.py`):
   - `periodic_y_strips`: every place where SWAN decides to cut its grid into
     x-strips (`MXC > MYC`, 22 places) must also require a non-periodic grid
     (`KREPTX .EQ. 0`), because SWAN's halo exchange never wraps around in x;
   - `periodic_coupled_stokes`: the coupler must take the spectral Stokes
     fields (`KSS`, `USS`, `VSS`) through the same index map (`isrc`) as the
     other wave fields.
2. **Standalone SWAN runs.** Builds `tests/cases/Swan_Periodic_Test` (SWAN
   only) before and after the patch. `make_inputs.py` writes an A15-like reef
   (A15's cross-shore profile from `a15_profile.txt`, one 200 m pass, 20 m
   mesh), periodic in x, with waves Hs 1 m, Tp 10 s from 20 deg east of north
   (oblique on purpose, so the seam matters), 1 h. Two grids:
   - `wide`: 4 km period, 200 x 121 points: more points in x than in y, so
     stock SWAN cuts it into x-strips (the crash or garbage case);
   - `tall`: 2 km period, 100 x 121: y-strips, the control.
   Each with 1 and with 4 SWAN processes.
3. **Checks** (`check_runs.py`), on Hs after 1 h:
   - `periodic_y_strips`: 4 processes = 1 process, bit for bit, on both grids;
   - `periodic_compgrid_frame`: `BLOCK 'COMPGRID'` output equals output on an
     explicit frame on the grid points, none missing.

## run_a15_coupled.sh, step by step

1. Builds `tests/cases/Reef_Ideal_A15` twice. A15's SWAN grid is curvilinear,
   and periodic curvilinear grids plus the case's NetCDF output are
   improvements later in the series, so both builds include them. The
   "before" build has every SWAN change except `periodic_coupled_stokes`
   (`tests/tools/variant_patches.sh` regenerates the SWAN patches without
   it); the "after" build has all. The only difference is this one change.
2. Runs each for 60 min (ROMS 1x2 + 2 SWAN by default), history every 10 min.
3. Checks: before, ROMS blows up or the Stokes drift exceeds 0.5 m/s; after,
   the run finishes with Stokes drift below 0.5 m/s.
   `plot_a15_coupled.py` draws the comparison.

## Running them

```bash
PYTHON=~/venv/bin/python tests/fixes/swan-periodic-fixes/run.sh COAWST-<ref>.tar.gz OUTDIR
PYTHON=~/venv/bin/python tests/fixes/swan-periodic-fixes/run_a15_coupled.sh COAWST-<ref>.tar.gz OUTDIR [MINUTES]
```

About 25 min and 40 min on 4 vCPUs. `run_a15_coupled.sh` takes `STAGES`
(`build run check`) to run the two cases elsewhere.

## Reading the output

```
periodic_y_strips  wide (x-strips): 4 vs 1 SWAN processes   max |diff| 1.35 m, Hs max 0.0198 m   BAD   (before)
periodic_y_strips  wide (x-strips): 4 vs 1 SWAN processes   bit-identical                         ok   (after)
...
before: blow-up yes, ..., max |Stokes drift| per record: 0.000, 0.163, 0.765, 1.442 m/s
after : blow-up no,  ..., max |Stokes drift| per record: 0.000, 0.040, 0.091, ..., 0.130 m/s
```

"Hs max 0.0198 m" in the 4-process stock run means SWAN produced garbage
(almost no waves) instead of crashing; the 1-process run has Hs up to 1.4 m.

## Last results

2026-10-30/31: both PASS. Details and a figure in the patch document.
