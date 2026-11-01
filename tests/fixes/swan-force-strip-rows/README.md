# Test: swan-force-strip-rows

Checks [`1-fixes/swan-force-strip-rows.patch`](../../../build/coawst/patches/1-fixes/swan-force-strip-rows.md):
SWAN's BLOCK output of the wave-driven force (`FORCE`) on several SWAN
processes must be complete and equal to the single-process output.

## The idea

The bug is about which process writes which point, so the number of SWAN
processes is what matters. One process has no strip boundaries and is the
reference; 2 and 3 processes put the boundaries in different places. The
waves themselves do not depend on the number of processes, so every value
must agree exactly. The change touches only output, so everything else must
be bit-identical before and after: the other outputs, and the coupled ROMS
run.

## What it does, step by step

1. **Builds** COAWST's Inlet_test (coupled ROMS + SWAN, 77 x 72 curvilinear
   grid, not periodic) before and after the patch (`tests/tools/build_pair.sh`).
2. **Runs** each build for 1 h on 1, 2 and 3 SWAN processes (ROMS on one),
   adding `BLOCK 'COMPGRID' ... 'force.mat' ... FORCE` every 30 min to the
   case's own BLOCK output (`tests/tools/run_inlet.sh` with `SWANSED`).
3. **Checks** (`check.py`), each PASS or FAIL:
   - *bug*: before, `FORCE` on 2 and 3 processes misses values that 1
     process has (it names the missing rows or columns);
   - *fixed*: after, `FORCE` on 2 and 3 processes equals 1 process exactly;
   - *unchanged*: every other `.mat` output on 1, 2 and 3 processes, and
     `FORCE` on 1, bit-identical before and after;
   - *roms*: the ROMS history bit-identical before and after.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/swan-force-strip-rows/run.sh OUTDIR
```

About 10 min to build and 15 min of runs on 4 vCPUs. `STAGES` (default
`build run check`) runs part of it.

## Last result

2026-10-31: PASS, on the control VM.

| Check | Result |
|---|---|
| bug | 2 processes: column 39 missing (280 values); 3 processes: columns 26 and 52 (536 values) |
| fixed | 2 and 3 processes identical to 1 |
| unchanged | 24 `.mat` outputs x 3 process counts bit-identical |
| roms | ROMS history bit-identical on 1, 2 and 3 SWAN processes |
