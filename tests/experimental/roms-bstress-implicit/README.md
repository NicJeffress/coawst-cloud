# Test: roms-bstress-implicit

Records what [`3-experimental/roms-bstress-implicit.patch`](../../../build/coawst/patches/3-experimental/roms-bstress-implicit.md)
(option `BSTRESS_IMPLICIT`) does on the idealized cases. It is a negative
result: on the realistic case it was written for, every run with it failed,
so this test is a record, not an accuracy test. (Options off:
[`options-off`](../options-off/README.md).)

## What it does, step by step

1. **Builds**, all with `-SPLINES_VVISC` (the option needs the tridiagonal
   vertical-viscosity solver), Reef_Ideal_A15 without and with the option,
   and Circle_Island with `+LIMIT_BSTRESS` (the cap the option replaces) and
   with the option.
2. **Runs** each for 1 h.
3. **Checks** (`check.py`): whether each run finished; differences in
   depth-mean current, sea level and Hs; the largest bottom stress. PASS if
   the two A15 runs finished.

## Running it

```bash
PYTHON=~/venv/bin/python tests/experimental/roms-bstress-implicit/run.sh OUTDIR
```

## Last result

2026-11-01: PASS (as a record), runs on Cloud Batch. All four runs finished.
A15 explicit vs implicit: currents within 4.6 cm/s at 99.9 % of cells
(largest 7.0 cm/s), bottom stress (99.9th pct) 6.23 vs 6.25 N m⁻². Circle
capped vs implicit: within 4.7 cm/s (largest 5.1), 1.30 vs 1.29 N m⁻². The
failure on the realistic case is not reproduced here.
