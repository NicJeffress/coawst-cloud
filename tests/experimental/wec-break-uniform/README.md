# Test: wec-break-uniform

Checks [`3-experimental/wec-break-uniform.patch`](../../../build/coawst/patches/3-experimental/wec-break-uniform.md)
with its option on (`WEC_BREAK_UNIFORM`): the wave-breaking acceleration is
then the same at every depth, where by default it is concentrated near the
surface. (Options off: [`options-off`](../options-off/README.md).)

## What it does, step by step

1. **Builds** Reef_Ideal_A15 (whose header has `DIAGNOSTICS_UV`) without and
   with the option.
2. **Runs** each for 1 h.
3. **Checks** (`check.py`): at the 50 places with the strongest breaking, the
   breaking acceleration in the top layer divided by that in the bottom layer
   (from `ocean_dia.nc`, `v_wbrk`); and how much the currents change. PASS if
   the ratio is 1 within 1 % with the option and above 2 (median) without.

## Running it

```bash
PYTHON=~/venv/bin/python tests/experimental/wec-break-uniform/run.sh OUTDIR
```

## Last result

2026-11-01: PASS, runs on Cloud Batch. Top/bottom breaking acceleration at
the 50 strongest points: 188 by default, 0.998 with the option. Currents
after 1 h: depth-mean up to 8.8 cm/s different, surface up to 13.8 cm/s.
