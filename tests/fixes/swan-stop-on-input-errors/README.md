# Test: swan-stop-on-input-errors

Checks [`1-fixes/swan-stop-on-input-errors.patch`](../../../build/coawst/patches/1-fixes/swan-stop-on-input-errors.md):
when SWAN rejects its input, the whole coupled run must stop at once and say
why.

## The idea

Give SWAN an input with a known error and see what COAWST does. Stock COAWST
should carry on (and, here, write out of bounds); the patched one should stop
cleanly. SWAN is built with run-time bounds checks so that the out-of-bounds
write stops the "before" run visibly instead of corrupting memory silently.

## What it does, step by step

1. Builds stock **Inlet_test** twice with SWAN compiled with `-fcheck=bounds`:
   with the patch series before this patch (`coawst-test:stoperr-before`) and
   with it (`-after`).
2. Adds one output request to `swan.in` that stock SWAN rejects:
   `BLOCK 'COMPGRID' NOHEADER 'wdirbot.nc' LAY 4 DIRBOT 1. OUTPUT ...`.
   DIRBOT (bottom wave direction) has no NetCDF name in stock SWAN, so SWAN
   reports "netCDF output not allowed" at error level 2, above the default
   `MAXERR` of 1.
3. Runs each image for 1 h (1 ROMS + 1 SWAN process).
4. Checks the run log and SWAN's PRINT file:

   | Run | Expected |
   |---|---|
   | before | "No start of computation", yet the run carries on, and stops later with a run-time error (out of bounds) |
   | after | stops at once with `SWAN input error level  2 > MAXERR`, no run-time error, and the PRINT file says "netCDF output not allowed for wdirbot.nc" |

## Running it

```bash
tests/fixes/swan-stop-on-input-errors/run.sh OUTDIR
```

About 15 min on 4 vCPUs. Needs only Docker.

## Reading the output

```
   before  SWAN refuses the input but the run carries on                ok
   before  and goes out of bounds                                       ok
   after   stops: SWAN input error level 2 > MAXERR                     ok
   after   no run-time error                                            ok
   after   PRINT file says what was wrong                               ok
-- before, log:
   At line 945 of file /opt/COAWST/SWAN/src_coawst/swanout1.f
   Fortran runtime error: Index '1' of dimension 1 of array 'voq' above upper bound of 0
-- after, log:
    SWAN input error level  2 > MAXERR: stopping, see SWAN PRINT file
PASS
```

## Last result

2026-10-30, control VM: PASS.
