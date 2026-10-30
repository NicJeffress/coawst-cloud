# Tests

## Checks on the patch series

| Script | What it checks |
|---|---|
| `same_source/compare_series.sh SOURCE SERIES_A DIR_A SERIES_B DIR_B` | Two patch series give the same COAWST source, file by file. Run it whenever the series is reordered, split or regenerated. |

Example: before a reorganisation, save the old series and its patches, then

```bash
tests/same_source/compare_series.sh COAWST-<ref>.tar.gz \
    old/series old/ build/coawst/patches/series build/coawst/patches/
```

prints `IDENTICAL: <n> files` or the files that differ.

## Tests of the patches

One folder per patch under `fixes/` (later `improvements/`, `experimental/`),
with a `run.sh` that builds what it needs before and after the patch, runs it,
compares, and prints PASS or FAIL. The results are written up in the patch's
document (`build/coawst/patches/<tier>/<patch>.md`).

| Test | Patch | What it shows | Time (4 vCPUs) |
|---|---|---|---|
| `fixes/roms-sed-morph-tiling/run.sh OUTDIR` | roms-sed-morph-tiling | Inlet_test 1x1 vs 1x2 tiles: differ before, bit-identical after | 40 min |
| `fixes/roms-wec-stokes-fixes/run.sh SOURCE OUTDIR` | roms-wec-stokes-fixes | source check of the u and v loops; Inlet_test before vs after | 15 min |
| `fixes/roms-limit-bstress/run.sh OUTDIR` | roms-limit-bstress | preprocessed Fortran of Veg_test, as shipped and `-WET_DRY +LIMIT_BSTRESS` | 15 min |
| `fixes/swan-nc-crash/run.sh OUTDIR` | swan-nc-crash | Inlet_test with SWAN bounds-checked: stops before, clean after | 15 min |
| `fixes/swan-stop-on-input-errors/run.sh OUTDIR` | swan-stop-on-input-errors | rejected SWAN request: carries on before, clean stop after | 15 min |
| `fixes/swan-output-fixes/run.sh OUTDIR` | swan-output-fixes | Inlet_test with points between grid points, NetCDF TABLE and BLOCK, 1 and 2 SWAN | 20 min |
| `fixes/swan-vegetation-fixes/run.sh SOURCE OUTDIR` | swan-vegetation-fixes | source check; Veg_test with VEGETATION 3, submerged and emergent plants | 25 min |

## Tools

| Script | Use |
|---|---|
| `tools/build_pair.sh PATCH TAG [build.sh args]` | builds TAG-before (series without PATCH and what follows) and TAG-after |
| `tools/series_upto.sh PATCH [--before]` | the series up to PATCH |
| `tools/patched_tree.sh SOURCE SERIES OUTDIR` | a COAWST source tree with a series applied, no build |
| `tools/run_inlet.sh IMAGE OUTDIR NAME [TI TJ NWAV HOURS]` | runs COAWST's Inlet_test with a chosen layout (Docker on this machine) |
| `tools/inlet_inside.sh [TI TJ NWAV HOURS]` | the same run, inside a coawst container (what `run_inlet.sh` calls; usable on a batch system) |
| `tools/run_project.sh IMAGE OUTDIR NAME PROJECT COUPLING OCEAN SWAN [TI TJ NWAV MINUTES]` | runs any COAWST project in the image (e.g. Projects/Veg_test) |
| `tools/project_inside.sh ...` | the same, inside a coawst container |
| `tools/compare_nc.py A.nc B.nc [VAR ...] [--last]` | largest difference per variable, bit-identical or not |

The Python scripts need numpy and netCDF4; the tests use `$PYTHON`
(default `python3`), e.g. `PYTHON=~/venv/bin/python tests/fixes/.../run.sh ...`.
