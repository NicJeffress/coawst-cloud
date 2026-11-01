# Test: roms-step2d-fb

Checks [`3-experimental/roms-step2d-fb.patch`](../../../build/coawst/patches/3-experimental/roms-step2d-fb.md)
with its option on (`STEP2D_FB_AB3_AM4`): the AB3-AM4 barotropic kernel
against COAWST's LF-AM3 and against a reference with smaller time steps, and
its speed. (That the build is unchanged with the option off is
[`options-off`](../options-off/README.md).)

## The idea

Two schemes for the same equations differ by their discretization errors.
Neither is "right", so each is compared with a reference whose time steps
are 4 times smaller (closer to the exact solution of the discrete-space
equations). AB3-AM4 should be about as close to it as LF-AM3, while costing
less: one kernel call per fast step instead of two.

## What it does, step by step

1. **Builds** Reef_Ideal_A15 and Circle_Island (whole series, `+PROFILE` for
   ROMS's timers), each with LF-AM3 and with `+STEP2D_FB_AB3_AM4`.
2. **Runs** each case for 1 h three ways: `lf` (LF-AM3, the case's DT and
   NDTFAST: A15 6 s and 24, Circle 4 s and 10), `fb` (AB3-AM4, the same),
   `ref` (LF-AM3, DT and the fast step 4 times smaller). Barotropic Courant
   numbers at the case settings: A15 0.81, Circle 0.18 (AB3-AM4's limit is
   about 0.89).
3. **Checks** (`check.py`): for sea level, depth-mean and 3-D currents and Hs,
   the largest and RMS difference of `lf` and of `fb` from `ref`, and of `fb`
   from `lf`; wall times and ROMS's time in the 2-D kernel. PASS if every run
   finished and `fb` is nowhere more than twice as far from `ref` as `lf`.

## Running it

```bash
PYTHON=~/venv/bin/python tests/experimental/roms-step2d-fb/run.sh OUTDIR
```

About 20 min to build; six 1-h runs (made on Cloud Batch for the results:
`STAGES=build`, runs into `OUTDIR/<case>-<run>/`, then `STAGES=check`).

## Last result

2026-11-01: PASS, runs on Cloud Batch. AB3-AM4 is as far from the
reference as LF-AM3 (largest differences within a few per cent, RMS within
about 10 %, on both cases). ROMS's 2-D kernel CPU time: A15 281 -> 110 s,
Circle 162 -> 68 s; 2-D halo exchanges 1.4-1.7x less; wall time 4-5 % less,
because ROMS then waits for SWAN. Details in the patch document.
