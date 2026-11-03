# Test: roms-quicksave-uv

Checks [`1-fixes/roms-quicksave-uv.patch`](../../../build/coawst/patches/1-fixes/roms-quicksave-uv.md):
the quicksave file's 3-D velocity `u`, `v` must be written.

## What it does

1. **Builds** tests/cases/Reef_Ideal_A15 with the whole series without
   (*before*) and with (*after*) this patch (the periodic SWAN of A15 needs
   the improvements tier, so a series cut at the patch would not run).
2. **Runs** 30 min each, ROMS 1 x 2 + 2 SWAN, history and quicksave every
   10 min, `Qout(idUvel)` and `Qout(idVvel)` on, the quicksave file in
   `output/` (all through `OCEANSED`).
3. **Checks** (`check.py`), each PASS or FAIL:
   - *bug*: before, quicksave `u`, `v` all fill values;
   - *fixed*: after, quicksave `u`, `v` equal the history `u`, `v` at every
     common time;
   - *unchanged*: the history files bit-identical before and after.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-quicksave-uv/run.sh /tmp/quickuv 30
```

About 5 min per build and 2-3 min per run on a 4-vCPU machine. Result of
2026-11-03: PASS.
