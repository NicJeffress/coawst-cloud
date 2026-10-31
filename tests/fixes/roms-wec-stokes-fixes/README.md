# Test: roms-wec-stokes-fixes

Checks [`1-fixes/roms-wec-stokes-fixes.patch`](../../../build/coawst/patches/1-fixes/roms-wec-stokes-fixes.md):
the u-point spectral Stokes drift loop in `wec_stokes.F` must be the mirror
image of the v-point loop.

## The idea

The bug is an inconsistency in the source code, so the exact test reads the
source: does every u-point average use the u-point neighbours, and do both
loops sum the same frequency bins? A model run then shows how much it matters.

## What it does, step by step

1. **Source check.** Makes the COAWST source with the patch series before
   this patch and with it (`tests/tools/patched_tree.sh`, no build), and runs
   `check_source.py` on `ROMS/Nonlinear/WEC/wec_stokes.F`. It finds the two
   loops that sum the spectrum (into `sdrx` for u, `sdry` for v) and checks:
   - every two-point average of a spectral field in the u loop uses
     `(i-1,j)` and `(i,j)`, never `(i,j-1)`; in the v loop the reverse;
   - both `DO WHILE` loops stop at `kD2deep`;
   - the u loop does not compute the unused `cff5`.
   Stock: INCONSISTENT; patched: CONSISTENT.
2. **Effect.** Builds stock Inlet_test before and after the patch and runs
   each for 2 h (argument `HOURS`), ROMS 1x2 + 1 SWAN, then compares the
   last history record of `u_stokes`, `v_stokes`, `ubar`, `vbar`, `zeta` and
   prints the wall times. This step reports numbers; it does not pass or fail
   (the size of the change depends on the case).

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-wec-stokes-fixes/run.sh COAWST-<ref>.tar.gz OUTDIR [HOURS]
```

`SOURCE` is the COAWST source at the pinned commit (a tarball, e.g. from
`build/coawst/vendor/`, or a clone). About 15 min on 4 vCPUs.

## Reading the output

```
-- before the patch
   u-point loop: 5 spectral averages, 1 use the i,j-1 neighbour
       cff3=0.5_r8*fac3*(spec_wn(i,j-1,is)+spec_wn(i,j,is))
   ...
   INCONSISTENT
-- after the patch
   ...
   CONSISTENT
== 2. Inlet_test, 2 h, before vs after
u_stokes                     0.001103      0.03006  (2, 7, 36, 43)   NO
```

The index of the largest `u_stokes` difference is (record, level, row,
column): row 36, column 43 is the inlet mouth.

## Last result

2026-10-30: source check PASS; u_stokes changed by up to 1.1 of 30 mm/s; ROMS
about 20 % faster (timing repeated on Cloud Batch). Details in the patch
document.
