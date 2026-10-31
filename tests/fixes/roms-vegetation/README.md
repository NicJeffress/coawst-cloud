# Test: roms-vegetation

Checks the four changes of
[`1-fixes/roms-vegetation.patch`](../../../build/coawst/patches/1-fixes/roms-vegetation.md)
on the idealized reef with a constant canopy,
[`tests/cases/Reef_Ideal_A15_veg`](../../cases/Reef_Ideal_A15_veg/README.md).

## What it does, step by step

1. **Source check** (`check_source.py`). Builds the COAWST source with the
   patch series up to, but not including, this patch, and with it, and reads
   the four places in the code:
   - `drag_work_array`: is `wrk` in `vegetation_drag.F` declared with the
     halo bounds `LBi:UBi,LBj:UBj`?
   - `zero_gap_stop`: does `vegetation_turb.F` stop when
     diameter x thickness x density >= 1?
   - `tau_veg_units`: is `tau_veg` computed from the plant work divided by
     the w-cell thickness (`Pveg`)?
   - `v_drag_depth`: does the v-point drag in `step2d_LF_AM3.h` use
     `Drhs(i,j-1)`?
   Stock COAWST must fail all four; the patched source must pass all four.
2. **Build** three images of the case. The case's SWAN setup (periodic on a
   curvilinear grid, many NetCDF outputs) needs two improvements that come
   later in the series, so every build includes them:
   - `before`: the fixes without this patch, + the two improvements
   - `after`: the fixes with this patch, + the two improvements
   - `nounits`: like `after`, but with the one line of `tau_veg_units`
     reverted (`Pveg = tke_loc_veg`), to measure what that change does
   It also writes `init_zero_gap.nc`: the case's initial file with the plants
   0.5 m thick instead of 0.39 m, so that diameter x thickness x density
   = 0.5 x 0.5 x 4 = 1.
3. **Run** the case (ROMS 1 x 2 tiles + 2 SWAN processes by default; set
   `TI`, `TJ`, `NWAV`):

   | Run | Image | Length | Expected |
   |---|---|---|---|
   | `before` | before | 30 min | crashes on the first step (heap corruption from the too-small work array) |
   | `after` | after | 60 min | runs to the end |
   | `zerogap` | after, `init_zero_gap.nc` | 10 min | stops at once: "plants cover the whole bed" |
   | `nounits` | nounits | 60 min | runs; its eddy viscosity is compared with `after` |
4. **Check** (`check_runs.py`): the crash, the clean run, the message; and the
   ratio of the canopy eddy viscosity (`AKv` at the w points inside the
   0.4 m canopy, last record) `after / nounits`, printed as the 10th, 50th
   and 90th percentiles. PASS needs the first three; the ratio is reported
   (it is the size of the physics change, not a pass/fail criterion).

`plot_units_effect.py OUTDIR FIGURE.png` draws the eddy-viscosity
comparison.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/roms-vegetation/run.sh COAWST-<ref>.tar.gz OUTDIR
```

`SOURCE` (first argument) is the COAWST source at the pinned commit, a
tarball or a folder, used for the source check. About 1.5 h on 4 vCPUs. To
run the four cases elsewhere (e.g. on a batch system, one machine each):
`STAGES="source build"`, run the cases with `tests/tools/case_inside.sh`
into `OUTDIR/<run>/`, then `STAGES=check`.

## Reading the output

```
drag_work_array    before: ROMS crashes at the start          SIGABRT          ok
drag_work_array    after: the case runs to the end            model exit 0     ok
zero_gap_stop      plants covering the bed: stops with a message ...           ok
                   | VEGETATION_TURB - plants cover the whole bed: ...
tau_veg_units      canopy AKv, patched / without units fix: 10/50/90 % = 0.827 / 0.895 / 0.956
ALL OK
```

A ratio below 1 means the fix lowers the canopy eddy viscosity: with the
correct units `tau_veg` is shorter, so the vegetation dissipation source is
stronger and less turbulence survives in the canopy.

## Last result

2026-10-31, runs on Cloud Batch (c2d-standard-8, ROMS 1 x 6 + 2 SWAN): PASS;
details in the patch document.
