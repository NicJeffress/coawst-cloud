# Test: roms-wec-stokes-fast

Checks [`2-improvements/roms-wec-stokes-fast.patch`](../../../build/coawst/patches/2-improvements/roms-wec-stokes-fast.md):
the spectral Stokes drift is computed faster and gives the same results to
rounding.

## The idea

The patch rewrites a formula exactly, so the same run before and after must
agree to the last bits, and the part of ROMS that contains the Stokes drift
must take less CPU time. ROMS measures its own parts when built with
`PROFILE`.

## What it does, step by step

1. **Builds** the idealized reef (`tests/cases/Reef_Ideal_A15`, coupled with
   SWAN, spectral Stokes drift) twice, before and after the patch, both with
   `CPP_OPTIONS="+PROFILE"`.
2. **Runs** each for MINUTES (default 60) on this machine (ROMS 1x2 + 2 SWAN;
   `TI`, `TJ`, `NWAV` change it). With `STAGES=build` the runs can be made
   elsewhere (for example on Cloud Batch) into `OUTDIR/before` and
   `OUTDIR/after`, then `STAGES=check`.
3. **Checks** (`check.py`):
   - *same physics*: the last history record of `u_stokes`, `v_stokes`,
     `ubar_stokes`, `vbar_stokes`, `u`, `v`, `zeta`, `AKv`, `tke`; the
     largest difference divided by the field's largest value must be below
     1e-5 (in practice about 1e-7, the last bit of single precision);
   - *speed*: the CPU time of ROMS's "Waves Effect on Currents kernel"
     before and after, from the profile at the end of each log; it must not
     grow.

## Running it

```bash
PYTHON=~/venv/bin/python tests/improvements/roms-wec-stokes-fast/run.sh OUTDIR [MINUTES]
```

About 10 min to build and 15 min per run on 4 vCPUs.

## Reading the output

```
    v            max |diff| 1.49e-07 (largest value 1.164, relative 1.3e-07); 8078 of 223300 points differ
ok  same physics: at 60 min, largest relative difference 1.8e-07 (limit 1e-5)
ok  speed: WEC kernel 372 -> 254 CPU-s summed over ROMS processes (-32 %); ...
```

Compare CPU times only between runs on the same kind of machine and layout;
VMs of the same type still differ by about 10 %.

## Last result

2026-10-31, runs on Cloud Batch (c2d-standard-8, ROMS 1x6 + 2 SWAN, 1 h):
PASS. Largest relative difference 1.8e-7; WEC kernel 372 -> 254 CPU-s
(-32 %). Wall time not shorter in this layout: ROMS waits for SWAN (see the
patch document).
