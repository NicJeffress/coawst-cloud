# Test: roms-ts-fixed-density

Checks [`1-fixes/roms-ts-fixed-density.patch`](../../../build/coawst/patches/1-fixes/roms-ts-fixed-density.md):
with `TS_FIXED`, a run stopped and restarted from its restart files must
continue exactly as the uninterrupted run.

## What it does

1. **Builds** with the fixes series without (*before*) and with (*after*)
   this patch: tests/cases/Reef_Ideal_A15_veg (`TS_FIXED`), and
   tests/cases/Reef_Ideal_A15 with `-TS_FIXED`.
2. **Runs** the `TS_FIXED` builds through tests/tools/restart_inside.sh (ROMS
   1 x 2 + 2 SWAN, DT 6 s): straight 0-60 min; 0-30 min writing restart files;
   30-60 min from them. The `-TS_FIXED` builds run 10 min with history every
   2 min.
3. **Checks** the double-precision restart records at 60 min, each PASS or FAIL:
   - *bug*: before, the restarted run differs from the straight one;
   - *fixed*: after, u, v, ubar, vbar and zeta are bit-identical;
   - *unchanged*: the builds without `TS_FIXED` write bit-identical history.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-ts-fixed-density/run.sh /tmp/tsfix
```

About 5 min per build (four builds) and 20 min for the restart runs on a
4-vCPU machine. Result of 2026-11-03: PASS (before: u differs at 443 050 points,
up to 5.4e-14 m/s; after: bit-identical; without `TS_FIXED` bit-identical).
