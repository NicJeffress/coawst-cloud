# Test: roms-wetdry-stokes

Checks [`1-fixes/roms-wetdry-stokes.patch`](../../../build/coawst/patches/1-fixes/roms-wetdry-stokes.md):
with wetting and drying on, the Stokes transport must not be dropped.

## The idea

In the idealized reef `tests/cases/Reef_Ideal_A15` nothing ever dries (the
shallowest water, 0.35 m on the crest at low tide, stays well above the
drying threshold of 0.10 m). So switching wetting and drying (`WET_DRY`) on
should leave the flow almost unchanged. If it changes the flow a lot, the
wet/dry code is doing something it should not: here, dropping the Stokes
transport towards -x and -y. Compare a run with `WET_DRY` against a run
without it, before and after the patch.

The run without `WET_DRY` gets `LIMIT_BSTRESS`, the bottom-stress cap that
`WET_DRY` switches on too (see `roms-limit-bstress`), so the only remaining
difference is wetting and drying itself.

## What it does, step by step

1. **Builds** four images of A15 (with the fixes and the two improvements A15's
   SWAN setup needs, `swan-netcdf-output` and `swan-periodic-curvilinear`):

   | Image | Options | Patch |
   |---|---|---|
   | `wetdry-wd-before` | `+WET_DRY` | without |
   | `wetdry-wd-after` | `+WET_DRY` | with |
   | `wetdry-nowd-before` | `+LIMIT_BSTRESS` | without |
   | `wetdry-nowd-after` | `+LIMIT_BSTRESS` | with |

2. **Checks the executables** of the two builds without `WET_DRY`: they must
   be bit-identical (md5), since the patch only touches `WET_DRY` code.
3. **Runs** `wd-before`, `wd-after` and `nowd-after` for 60 min (argument
   `MINUTES`), history every 10 min.
4. **Compares** (`check_runs.py`) each `WET_DRY` run with the run without it:
   the largest difference in `ubar`, `vbar` and `zeta` at every record.
   PASS: before the patch > 1 cm/s at the last record (the bug), after it
   < 1 mm/s.

`plot_wetdry.py OUTDIR FIGURE.png` draws the comparison.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-wetdry-stokes/run.sh OUTDIR [MINUTES]
```

About 15 min to build and about 1.5 h to run on 4 vCPUs (ROMS 1x2 + 2 SWAN by
default; `TI`, `TJ`, `NWAV` change the layout). With `STAGES=build` the runs
can be made elsewhere (one machine each), then `STAGES=check`.

## Reading the output

```
   builds without WET_DRY: identical executables          ok
WET_DRY before the patch vs no WET_DRY, largest |difference| per record:
      10 min: ubar 1.15e-05 m/s, vbar 1.45e-05 m/s, zeta 6.69e-07 m
      ...
      60 min: ubar 2.24e-01 m/s, vbar 2.43e-01 m/s, zeta 1.22e-02 m
WET_DRY after the patch vs no WET_DRY, largest |difference| per record:
      ...
      60 min: ubar 6.16e-05 m/s, vbar 1.14e-05 m/s, zeta 9.00e-07 m
before: 2.43e-01 m/s (> 1e-2: bug shown)   after: 6.16e-05 m/s (< 1e-3)   ok
PASS
```

## Last result

2026-10-31 (runs on Cloud Batch, c2d-standard-8, ROMS 1x6 + 2 SWAN): PASS.
