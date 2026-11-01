# Test: experimental options off

Checks the promise of the experimental tier
([`build/coawst/patches/3-experimental/`](../../../build/coawst/patches/)):
each of those patches acts only when its cpp option is defined, so a build
without the options is the same with and without them.

| Patch | Option |
|---|---|
| `roms-step2d-fb` | `STEP2D_FB_AB3_AM4` |
| `roms-veg-implicit` | `VEG_DRAG_IMPLICIT` |
| `roms-bstress-implicit` | `BSTRESS_IMPLICIT` |
| `wec-break-uniform` | `WEC_BREAK_UNIFORM` |

## The idea

ROMS's build preprocesses every source file (cpp) into the Fortran that is
compiled (`Build_roms/*.f90`). If an option is off, the code it guards
disappears there. Comparing those files with and without the patches shows
directly whether anything else changed, without depending on which paths a
test run happens to exercise.

## What it does, step by step

1. **Builds** (build stage only) four configurations twice, with the series
   without the `3-experimental` patches and with the whole series:
   - `inlet`: COAWST's Inlet_test (sediment, morphology, WEC, SWAN);
   - `a15veg`: Reef_Ideal_A15_veg (vegetation drag and turbulence, WEC_VF,
     SSW_BBL, GLS, periodic);
   - `a15wetdry`: Reef_Ideal_A15 with `+WET_DRY` (the patched `wetdry.F`);
   - `circle`: Circle_Island (curvilinear O-grid).
2. **Compares** the preprocessed files (`compare.py`). They must be the same,
   except for two kinds of line that cannot change what is computed:
   - comment lines;
   - integers in calls that carry `MyFile`: ROMS passes the source line
     number (`__LINE__`) with the file name to its timers and error messages,
     and the patches, by adding lines, shift those numbers.

   Any other difference fails the test.

## Running it

```bash
PYTHON=~/venv/bin/python tests/experimental/options-off/run.sh OUTDIR
```

About 1 h on 4 vCPUs (eight builds). `STAGES=check` compares existing
outputs.

## Last result

2026-11-01: PASS. 405 preprocessed files per configuration. In all four,
`step3d_uv.f90` differs in two line numbers (the `wclock_on`/`wclock_off`
calls of ROMS's timer); in `a15veg`, `vegetation_drag.f90` has one comment
line more. Nothing else differs.
