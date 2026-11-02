# Test: roms-vandera-no-sand

Checks [`1-fixes/roms-vandera-no-sand.patch`](../../../build/coawst/patches/1-fixes/roms-vandera-no-sand.md):
with van der A bedload and no sand class, the van der A output fields must be
zero, not unset memory; with sand, nothing may change.

## The idea

Memory that is never set holds leftovers that change from build to build, so
a test cannot predict them. Compiling ROMS with `-finit-real=snan` fills
unset local variables with NaN instead, so "never set" becomes visible:
before the patch the written `fd_wbl` must contain NaN, after it zero.

## What it does, step by step

1. Builds four images, before and after the patch (the series up to it):
   - COAWST's **Inlet_test DiffGrid** (mud only: `NCS = 1`, `NNS = 0`; van der
     A bedload with `BEDLOAD_VANDERA_MADSEN_UDELTA`), with
     `ROMS_FFLAGS_EXTRA="-finit-real=snan"`: `coawst-test:vns-diffgrid-before`
     and `-after`;
   - COAWST's **Inlet_test Coupled** (one sand class), usual flags:
     `coawst-test:vns-inlet-before` and `-after`.
2. Runs each for 2 simulated hours (argument `MINUTES`, default 120):
   DiffGrid with ROMS 2x2 + 2 SWAN (`tests/tools/run_project.sh`), Coupled with
   ROMS 1x2 + 1 SWAN (`tests/tools/run_inlet.sh`).
3. [`check.py`](check.py) compares the history files:
   - DiffGrid before: `fd_wbl` has NaN at water points;
   - DiffGrid after: `fd_wbl`, and any other van der A field in the file
     (`Ursell_number`, `velocity_skewness`, ...), is zero everywhere;
   - DiffGrid: every other variable bit-identical before vs after;
   - Inlet_test Coupled: every variable bit-identical before vs after.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-vandera-no-sand/run.sh OUTDIR [MINUTES]
```

About 15 min of builds and 10 min of runs on 4 vCPUs. Needs Docker and Python
with numpy and netCDF4. `STAGES="check"` re-reads existing runs.

## Reading the output

```
DiffGrid (mud only), van der A fields written: fd_wbl
PASS  DiffGrid before: fd_wbl unset (NaN): 10666 of 15999 water values NaN
PASS  DiffGrid after: fd_wbl is zero: 0 NaN, largest |value| 0
PASS  DiffGrid: every other variable bit-identical before vs after: 193 compared
PASS  Inlet_test Coupled (sand): every variable bit-identical before vs after: 211 compared, fd_wbl in the file
PASS
```

(2026-11-02). The first of the three history records is the initial state,
written before the bedload routine first runs, so it is zero on both sides.
