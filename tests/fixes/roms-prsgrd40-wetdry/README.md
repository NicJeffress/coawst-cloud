# Test: roms-prsgrd40-wetdry

Checks [`1-fixes/roms-prsgrd40-wetdry.patch`](../../../build/coawst/patches/1-fixes/roms-prsgrd40-wetdry.md):
the `PJ_GRADP` pressure-gradient scheme must compile with `WET_DRY`, and
nothing else may change.

## The idea

The bug is a compile error, so the test is mostly about builds:
- before the patch, `PJ_GRADP` + `WET_DRY` must stop on the undeclared
  wet/dry masks;
- after the patch, the same build must compile;
- without `WET_DRY`, the executables before and after must be identical.

A short run then shows the newly possible build actually works.

## What it does, step by step

1. Builds the idealized reef case [`tests/cases/Reef_Ideal_A15`](../../cases/Reef_Ideal_A15/README.md)
   four times. Every build has all the fixes, plus the two improvements A15's
   SWAN setup needs (`swan-netcdf-output`, `swan-periodic-curvilinear`), and
   `CPP_OPTIONS="-DJ_GRADPS +PJ_GRADP"`. The four:
   - `pgwd-before`: `+WET_DRY`, without this patch;
   - `pgwd-after`: `+WET_DRY`, with it;
   - `pg-before`, `pg-after`: without `WET_DRY`.
2. Checks:
   - `pgwd-before` fails with gfortran's "Symbol 'umask_wet' ... has no
     IMPLICIT type";
   - `pgwd-after` compiles;
   - `pg-before` and `pg-after` have the same `coawstM` (md5).
3. Runs `pgwd-after` for `MINUTES` (default 30) on ROMS 1x2 + 2 SWAN
   (`tests/tools/run_case.sh`) and checks that the history file's sea level
   and currents are finite.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-prsgrd40-wetdry/run.sh OUTDIR [MINUTES]
```

About 20 minutes of builds plus the run, on 4 vCPUs. Needs Docker and Python
with numpy and netCDF4. `TI`, `TJ`, `NWAV` set the run's layout.

## Reading the output

```
== builds
PASS  PJ_GRADP + WET_DRY before the patch: does not compile ('umask_wet' 'vmask_wet' have no IMPLICIT type)
PASS  PJ_GRADP + WET_DRY with the patch: compiles
PASS  PJ_GRADP without WET_DRY: identical executables before and after (80d409076580deed01d33f124fb094be)
== run: PJ_GRADP + WET_DRY with the patch, 30 min, ROMS 1x2 + 2 SWAN
PASS  run with the patch: 4 records to 30 min, largest |u| at the end 0.297 m/s, all finite
PASS
```

(2026-11-02, the control VM.) The run writes history every 10 minutes
(`OUTDT=10`), since the case's own interval is an hour. A15 never dries, so
the masks are 1 everywhere; the run shows that the build works, not how
`PJ_GRADP` performs.
