# Test: roms-stokes-interval

Checks [`3-experimental/roms-stokes-interval.patch`](../../../build/coawst/patches/3-experimental/roms-stokes-interval.md).

## What it does, step by step

Runs on Cloud Batch, with an image built with `--build-arg CPP_OPTIONS="+STOKES_INTERVAL"` and `STOKES_NCPL` in `ocean.in`:

1. **Control:** `STOKES_NCPL` 0 for 2 h, against a build without the patch. `check.py` must find no differences.
2. **Restart:** `STOKES_NCPL` 1 for 8 h with a restart at 4 h, against the straight run. From the second record after the restart, `check.py` must find no differences. In the first, only output-only fields and diagnostics may differ.
3. **Accuracy:** `STOKES_NCPL` 1, 5, 20 for 24 h, against `STOKES_NCPL` 0. Compare set-up, transports, the budget and turbulence.
4. **Noise floor:** the same case without the option, with white noise of 1e-9, 1e-6 and 1e-3 m added to the initial `zeta`. A difference between intervals counts as real only if it is larger than these.

## Running it

```bash
~/venv/bin/python tests/experimental/roms-stokes-interval/check.py BASE_DIR RUN_DIR
```

## Last result

2026-11-05, coawst-cloud `ca5316d` plus this patch: control and restart pass. Accuracy numbers are in the patch's document.

Noise floor, `u` difference from the run without noise in hourly snapshots, % of the field's rms, 3-5 km from shore:

| Hour | Noise 1e-9 m | 1e-6 m | 1e-3 m | `STOKES_NCPL` 20 | 5 | 1 |
|---|---|---|---|---|---|---|
| 6 | 0.0006 | 0.002 | 0.05 | 0.8 | 2.0 | 10 |
| 12 | 0.002 | 0.007 | 0.13 | 2.6 | 8.7 | 17 |
| 18 | 0.006 | 0.03 | 0.96 | 15 | 26 | 36 |
| 24 | 0.06 | 0.56 | 9.4 | 39 | 50 | 53 |

- That far offshore the flow amplifies differences (noise grows about 40-150x from hour 12 to 24), but noise alone doesn't reach the option's size in a day. At hour 6 the option's difference scales with the interval; by hour 24 it has levelled off.
- On the reef and in the lagoon the noise stays under 0.001 mm of set-up and 0.001 m³/s of transport, below the option's changes (-0.0008 mm, +0.002 m³/s at `STOKES_NCPL` 5 for the same run), which are real and small.
- Tide means, hours 12-24, offshore-going transport against every step: `STOKES_NCPL` 20 within 0.13 % at every line; 5 about +0.9 % at 3.5-4 km and -4.4 % at 4.9 km; 1 -10 % at 4.9 km. Noise of 1e-3 m: -0.4 % at 4.9 km at most.
