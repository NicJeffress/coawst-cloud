# Test: roms-veg-implicit

Checks [`3-experimental/roms-veg-implicit.patch`](../../../build/coawst/patches/3-experimental/roms-veg-implicit.md)
with its option on (`VEG_DRAG_IMPLICIT`): implicit canopy drag removes the
time-step limit of the explicit drag and stays close to an explicit run that
is stable. (Options off: [`options-off`](../options-off/README.md).)

## The idea

A dense canopy (0.5 Cd D n = 1 m⁻¹) with currents near 1 m/s makes the
explicit drag unstable at A15's DT of 6 s. The patchy canopy of
`tests/cases/Reef_Ideal_A15_veg/make_patchy_init.py` (dense and sparse
patches with bare gaps over the reef) has exactly that. The explicit drag at
DT 3 s is stable and serves as the reference; the implicit drag at 6 s must
run and stay close to it.

## What it does, step by step

1. **Builds** a copy of Reef_Ideal_A15_veg with the patchy initial file added,
   without and with `+VEG_DRAG_IMPLICIT` (whole series).
2. **Runs** 1 h each (ROMS 1x6 + 2 SWAN): patchy canopy explicit and implicit
   at DT 6 s and 3 s; the case's uniform canopy explicit and implicit at 6 s.
3. **Checks** (`check.py`): which runs finished (the explicit DT 6 s patchy
   run is expected to blow up); the depth-mean current differences of the
   implicit runs from the explicit reference. PASS if every implicit run and
   both references finished and implicit DT 6 s is within 2 cm/s of the
   reference at 99.9 % of the cells.

## Running it

```bash
PYTHON=~/venv/bin/python tests/experimental/roms-veg-implicit/run.sh OUTDIR
```

About 10 min to build; six 1-h runs (Batch for the results, as above).

## Last result

2026-11-01: PASS, runs on Cloud Batch. Patchy canopy: explicit DT 6 s blew up
between 40 and 50 min; implicit DT 6 s ran and is within 1.0 cm/s of the explicit
DT 3 s reference at 99.9 % of the cells (20 of 21708 cells above 1 cm/s,
largest 1.4 cm/s). Implicit DT 3 s vs explicit DT 3 s within 0.6 cm/s;
uniform canopy implicit vs explicit at 6 s within 0.3 cm/s.
