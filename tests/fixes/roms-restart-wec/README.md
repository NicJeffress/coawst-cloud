# Test: roms-restart-wec

Checks [`1-fixes/roms-restart-wec.patch`](../../../build/coawst/patches/1-fixes/roms-restart-wec.md):
a coupled ROMS + SWAN run stopped and restarted from its restart files must
continue as the uninterrupted run.

## The idea

Run the same case twice: once straight through for 60 min, and once stopped
at 30 min and restarted from the files it wrote then. If the restart is
exact, the two agree at 60 min to round-off (differences of order 1e-10 m/s,
from the different order of floating-point operations). Do it before and after
the patch, on two variants that exercise different parts of the fix.

## What it does, step by step

1. **Builds** two variants of the idealized reef, before and after the patch
   (4 images). All builds have the other fixes (including SWAN's own restart
   fix, `swan-exact-restart`) and the two improvements A15's SWAN setup needs.
   - `veg`: `tests/cases/Reef_Ideal_A15_veg`: waves, a canopy everywhere, GLS
     turbulence.
   - `river`: `tests/cases/Reef_Ideal_A15` with a river: `make_river.py`
     writes three face sources on the land wall at the south of the lagoon
     (5 m3/s each, in the top layers); the test switches them on with
     `LuvSrc == T`.
2. **Runs** each image with `tests/tools/restart_inside.sh` (three runs in a
   row in one container):
   - `straight`: 0 -> 60 min;
   - `part1`: 0 -> 30 min, writing ROMS's restart record (`PERFECT_RESTART`)
     and SWAN's binary restart files at 30 min;
   - `part2`: 30 -> 60 min, starting from part1's files.
   History and SWAN output every 10 min.
3. **Checks** (`check_runs.py`): the largest difference between part2 and
   straight at 60 min in `ubar`, `vbar`, `u`, `v`, `zeta`, `AKv`, `tke` and
   SWAN's Hs. It also runs the river image with the river switched off
   (`noriver-after`): the base A15 case restarts to about 1e-7 m/s, a small
   residual unrelated to rivers (see the patch document), which is the
   baseline for the river variant. PASS needs a difference above 1e-6 m/s
   before the patch, and after it below 1e-8 m/s (veg) or no more than 3 times
   the no-river baseline (river).

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-restart-wec/run.sh OUTDIR [TOTAL RST]
```

About 20 min to build and 2.5 h to run on 4 vCPUs (ROMS 1x2 + 2 SWAN; `TI`,
`TJ`, `NWAV` change it). With `STAGES=build` the four runs can be made
elsewhere (one machine each; OUTDIR/<variant>-<side>/ as
`restart_inside.sh` writes it), then `STAGES=check`.

## Reading the output

```
veg   before at 60/60 min: currents 2.7e-05 m/s; ubar 1.0e-05, ...; SWAN Hs 6.9e-06 m
veg   after  at 60/60 min: currents 1.2e-10 m/s; ...; SWAN Hs 0.0e+00 m
veg   restarted vs straight: before 2.7e-05, after 1.2e-10 m/s  ok
```

"currents" is the largest of the velocity differences; "SWAN Hs 0.0e+00"
means SWAN's output is bit-identical.

## Last result

2026-10-31, runs on Cloud Batch: PASS. veg: 2.7e-5 -> 1.2e-10 m/s (SWAN
bit-identical); river: 2.1e-2 -> 2.4e-7 m/s, baseline without the river
1.8e-7 m/s. Details in the patch document.
