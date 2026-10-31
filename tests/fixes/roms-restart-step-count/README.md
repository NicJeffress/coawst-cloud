# Test: roms-restart-step-count

Checks [`1-fixes/roms-restart-step-count.patch`](../../../build/coawst/patches/1-fixes/roms-restart-step-count.md):
a perfect restart whose step number, `(time - DSTART)/DT + 1`, does not fit
ROMS's step counter must stop with a message instead of continuing wrongly.

## The idea

The overflow happens when the start time is far from `DSTART`, for example
an initial file dated 2000-01-01 with `DSTART = 0` (730119 days apart). The
test makes the same distance on Reef_Ideal_A15, whose initial time is 0 days,
by setting `DSTART = -730119` days (the "far" variant). It then compares the
patched and unpatched builds on this variant and on the case as it is (the
"normal" variant).

## What it does, step by step

1. **Builds** Reef_Ideal_A15 before and after the patch (all fixes, plus the
   two improvements A15's SWAN setup needs).
2. **Runs** each image with `tests/tools/restart_inside.sh` in both
   variants: `straight` 0 -> 60 min, `part1` 0 -> 30 min writing restart
   files, `part2` 30 -> 60 min from them (ROMS 1x2 + 2 SWAN here).
3. **Checks** (`check.py`), each PASS or FAIL:
   - *bug*: far-before: the restarted run does not continue the straight one;
   - *stops*: far-after: part2 stops at once with "GET_STATE - perfect
     restart: the step number ..." and writes no history;
   - *warns*: far-after: the fresh runs print "GET_STATE - warning" and equal
     the normal runs bit for bit (except the stored `dstart`); the normal
     runs print no warning;
   - *exact*: normal restarts exactly (< 1e-8 m/s), before and after;
   - *unchanged*: normal before = after, bit for bit.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-restart-step-count/run.sh OUTDIR
```

About 10 min to build and 4 x 15 min of runs on 4 vCPUs. With
`STAGES=build`, make the runs elsewhere into `OUTDIR/<variant>-<side>/`, then
`STAGES=check`.

## Last result

2026-10-31: PASS, runs on Cloud Batch (ROMS 1x6 + 2 SWAN).

| Check | Result |
|---|---|
| bug | far-before: step counter wrapped to 1,923,779,008; history at 552, 1152, ... s; restarted run ends at 2352 s, no common record |
| stops | far-after part2: message, exit 1, no history |
| warns | far-after fresh runs warn and equal normal-after bit for bit |
| exact | normal: 4.7e-10 m/s before and after |
| unchanged | normal straight, part1, part2 bit-identical before and after |
