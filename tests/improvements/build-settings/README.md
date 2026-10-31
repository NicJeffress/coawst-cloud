# Test: build settings

Checks the build settings of the engine's Dockerfile
([`2-improvements/build-settings.md`](../../../build/coawst/patches/2-improvements/build-settings.md)),
which are not patches to COAWST's source but changes to how it is compiled:
ROMS without `-ffast-math`, SWAN at `-O3` instead of `-O1`, both with
`-march=x86-64-v3 -g`, and `SWAN_SINGLESPEC` off. `BUILD_SETTINGS=stock`
builds with COAWST's own choices, so the two can be compared from one
Dockerfile.

## The idea

- `SWAN_SINGLESPEC` affects only how SWAN writes spectra at output points.
  With it, more than one SWAN process should still give the same spectra as
  one process; the test checks that.
- The compiler flags change the order and precision of floating-point
  operations, not the equations. The same run built both ways must stay
  close (rounding differences grow a little in a turbulent flow, but must
  stay far below anything physical), and the test measures the speed.
- A build is useful for ensembles only if it reproduces itself: the same
  image run again, and on another kind of machine, must give the same
  numbers.

## What it does, step by step

1. **Builds** Inlet_test and Reef_Ideal_A15, each with
   `BUILD_SETTINGS=stock` and `=engine` (all patches up to
   `roms-wec-stokes-fast` in all four).
2. **Runs**
   - Inlet_test, 2 h, on 1 and on 2 SWAN processes, with `SPECOUT` (text
     and NetCDF) at 9 points spread over the domain, so both SWAN processes
     own some, plus the case's own `point1.spc2d`;
   - Reef_Ideal_A15, 1 h, twice with each image (`a15-<settings>-<machine>-<k>`).
     Runs on other machine types are made elsewhere (for example Cloud Batch
     on AMD c2d and Intel n2 machines) into the same layout.
3. **Checks** (`check.py`):
   - *specout*: with the engine settings, 2 SWAN processes give the same
     spectra as 1 (text equal up to trailing blanks, every NetCDF variable
     equal); with the stock settings the result is reported (broken);
   - *repeat*: runs of the same image on the same machine type identical;
   - *machines*: AMD vs Intel, same image (reported);
   - *flags*: engine vs stock after 1 h, largest relative difference below
     1e-2 (reported in full);
   - *speed*: wall times (reported).

## Running it

```bash
PYTHON=~/venv/bin/python tests/improvements/build-settings/run.sh OUTDIR
```

About 40 min to build four images, then 10 min for Inlet_test and about
30 min for the A15 runs on 4 vCPUs. With `STAGES=build`, run the A15
images elsewhere into `OUTDIR/a15-<settings>-<machine>-<k>/`, then
`STAGES=check`.

## Last result

2026-10-31: PASS. Inlet_test on the control VM, A15 on Cloud Batch (ROMS
1x6 + 2 SWAN; AMD c2d-standard-8, three runs per image; Intel n2-standard-8,
one). `SPECOUT` on 2 SWAN processes: stock truncated (text 59 of 174 kB,
NetCDF unreadable), engine equal to 1 process. Repeats and AMD vs Intel
identical for both settings. Engine vs stock after 1 h: largest relative
difference 5.6e-5. A15 wall time 267 s -> 152 s (AMD), 315 s -> 198 s
(Intel). Details in the settings document.
