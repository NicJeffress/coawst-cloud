# Test: swan-nc-crash

Checks [`1-fixes/swan-nc-crash.patch`](../../../build/coawst/patches/1-fixes/swan-nc-crash.md):
SWAN's NetCDF output must not read or write past the end of a file name or
of its NetCDF name table.

## The idea

Out-of-bounds memory accesses usually go unnoticed, or crash at random
later. gfortran can check every array and string access at run time
(`-fcheck=bounds`) and stop at the first bad one, with the file and line. So
build SWAN with that check, run a case that exercises the code, and see
whether it stops.

## What it does, step by step

1. Builds stock **Inlet_test** twice, with SWAN compiled with
   `-fcheck=bounds` (build argument `SWAN_FFLAGS_EXTRA`): with the patch
   series before this patch (`coawst-test:nccrash-before`) and with it
   (`-after`).
2. Runs each for 1 h, 1 ROMS + 1 SWAN process, in two variants:
   - `shipped`: the case as it is. It writes Hs to `hsig.nc`, which goes
     through the file-opening routine `FOR` with an 11-character name
     (`nc_filename_length`).
   - `dirbot`: plus one NetCDF output request for `DIRBOT`, SWAN quantity
     number 200, which makes SWAN look it up in the 171-row name table
     (`stnames_size`).
3. Checks the logs for the run-time errors:

   | Run | Expected |
   |---|---|
   | shipped-before | `Actual string length is shorter than the declared one for dummy argument 'ddname' (11/140)` |
   | shipped-after | no run-time error, the run reaches its end |
   | dirbot-before | `Index '200' of dimension 1 of array 'stnames' above upper bound of 171` |
   | dirbot-after | no error about `stnames` |

The `dirbot-after` run still fails, later: SWAN rightly rejects the request
(DIRBOT has no NetCDF name before the netcdf-output improvement) but COAWST
carries on regardless. That is the next bug, tested by
[`swan-stop-on-input-errors`](../swan-stop-on-input-errors/README.md).

## Running it

```bash
tests/fixes/swan-nc-crash/run.sh OUTDIR
```

About 15 min on 4 vCPUs. Needs only Docker.

## Reading the output

```
== run-time errors (SWAN with -fcheck=bounds)
   shipped-before   stops in FOR: file name read past its end        ok
   shipped-after    no run-time error                                ok
   shipped-after    runs to the end                                  ok
   dirbot-before    stops: name table indexed past its end           ok
   dirbot-after     no error about the name table                    ok
-- shipped-before:
   At line 1592 of file /opt/COAWST/SWAN/src_coawst/ocpmix.f
   Fortran runtime error: Actual string length is shorter than ... (11/140)
...
PASS
```

## Last result

2026-10-30, control VM: PASS.
