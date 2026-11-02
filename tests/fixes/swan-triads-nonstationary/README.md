# Test: swan-triads-nonstationary

Checks [`1-fixes/swan-triads-nonstationary.patch`](../../../build/coawst/patches/1-fixes/swan-triads-nonstationary.md):
with currents and one SWAN iteration per time step (every coupled run with
SWAN's defaults), `TRIAD` must actually compute triads.

## The idea

SWAN writes the triad energy transfer as the BLOCK quantity `REDTRIAD`. If
triads never run, it is zero everywhere, and removing the `TRIAD` line from
`swan.in` changes nothing at all. With the patch it is nonzero where waves
shoal over the reef, and the run with `TRIAD` removed must still be
bit-identical to the unpatched run: the patch touches only the triad branch.

## What it does, step by step

1. **Builds** tests/cases/Reef_Ideal_A15_veg (coupled ROMS + SWAN, periodic,
   a canopy everywhere, waves ramped to Hs 1 m over 30 min) with the whole
   series without this patch (*before*) and with it (*after*).
2. **Runs** 60 min each, ROMS 1 x 2 + 2 SWAN, output every 10 min:
   *before* and *after* with `TRIAD`, *after-notriad* with the line removed
   (`SWANSED='/^TRIAD *$/d'`).
3. **Checks** (`check.py`), each PASS or FAIL:
   - *bug*: before, `REDTRIAD` zero at every point and output time;
   - *fixed*: after, `REDTRIAD` nonzero, and Hs different from before;
   - *unchanged*: after-notriad bit-identical to before in every output file.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/swan-triads-nonstationary/run.sh /tmp/triads 60
```

About 5 min per build and 5 min per run on a 4-vCPU machine
(`MPIRUN_ARGS=--oversubscribe` is set). `STAGES="check"` reruns only the
checks. Result of 2026-11-02: PASS (numbers in the patch document).
