# Test: roms-roller-substeps

Checks [`1-fixes/roms-roller-substeps.patch`](../../../build/coawst/patches/1-fixes/roms-roller-substeps.md):
the Reniers roller must run at DT 6 s on the A15 reef.

## What it does

1. **Builds** tests/cases/Reef_Ideal_A15 with the whole series without
   (*before*) and with (*after*) this patch, each with `+ROLLER_RENIERS` and
   as the case stands (no roller).
2. **Runs** the two roller builds for 40 min, ROMS 1 x 2 + 2 SWAN, DT 6 s,
   `WEC_ALPHA` 0.5 (through `OCEANSED`).
3. **Checks**, each PASS or FAIL:
   - *bug*: before, ROMS blows up (about 21 min, at the inner edge of the
     crest beside the pass);
   - *fixed*: after, the run reaches 40 min;
   - *unchanged*: the builds without the roller give identical executables
     (the change is inside `ROLLER_RENIERS`).

## Running it

```bash
tests/fixes/roms-roller-substeps/run.sh /tmp/roller 40
```

About 5 min per build (four builds) and 2-3 min per run on a 4-vCPU
machine. Result of 2026-11-03: PASS (before: blow-up at 21.4 min, step 214).
The 24 h accuracy check (DT 6 s against DT 3 s) is in the patch document.
