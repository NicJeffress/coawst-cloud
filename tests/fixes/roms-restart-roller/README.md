# Test: roms-restart-roller

Checks [`1-fixes/roms-restart-roller.patch`](../../../build/coawst/patches/1-fixes/roms-restart-roller.md):
with `ROLLER_RENIERS`, a run stopped and restarted from its restart files must
continue as the uninterrupted run.

## What it does

1. **Builds** tests/cases/Reef_Ideal_A15 with the fixes series without
   (*before*) and with (*after*) this patch, each with `+ROLLER_RENIERS` and
   as the case stands (no roller).
2. **Runs** the two roller builds (tests/tools/restart_inside.sh, ROMS 1 x 2 +
   2 SWAN, DT 6 s, `WEC_ALPHA` 0.5 through `OCEANSED`): straight 0-60 min;
   0-30 min writing restart files; 30-60 min from them. The two builds without
   the roller run 10 min each with history every 2 min.
3. **Checks**, each PASS or FAIL:
   - *bug*: before, the restarted run is more than 1e-6 m/s off the straight
     one at 60 min;
   - *fixed*: after, less than 1e-8 m/s (round-off);
   - *unchanged*: the builds without the roller write bit-identical history
     (their executables differ, since ROMS's error calls carry line numbers).

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-restart-roller/run.sh /tmp/rstroller
```

About 5 min per build (four builds) and 15-25 min for the roller runs on a
4-vCPU machine. Result of 2026-11-03: PASS (before 6.4e-4 m/s, after
5.8e-11 m/s, without the roller bit-identical).
