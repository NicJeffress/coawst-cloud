# Test: roms-stokes-interval

Checks [`3-experimental/roms-stokes-interval.patch`](../../../build/coawst/patches/3-experimental/roms-stokes-interval.md).

## What it does, step by step

Runs on Cloud Batch, with an image built with `--build-arg CPP_OPTIONS="+STOKES_INTERVAL"` and `STOKES_NCPL` in `ocean.in`:

1. **Control:** `STOKES_NCPL` 0 for 2 h, against a build without the patch. `check.py` must find no differences.
2. **Restart:** `STOKES_NCPL` 1 for 8 h with a restart at 4 h, against the straight run. From the second record after the restart, `check.py` must find no differences. In the first, only output-only fields and diagnostics may differ.
3. **Accuracy:** `STOKES_NCPL` 1, 5, 20 for 24 h, against `STOKES_NCPL` 0. Compare set-up, transports, the budget and turbulence.

## Running it

```bash
~/venv/bin/python tests/experimental/roms-stokes-interval/check.py BASE_DIR RUN_DIR
```

## Last result

2026-11-05, coawst-cloud `ca5316d` plus this patch: control and restart pass. Accuracy numbers are in the patch's document.
