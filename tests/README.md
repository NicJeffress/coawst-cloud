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

One folder per patch under `fixes/`, `improvements/` (later `experimental/`),
with a `run.sh` that builds what it needs before and after the patch, runs it,
compares, and prints PASS or FAIL. The results are written up in the patch's
document (`build/coawst/patches/<tier>/<patch>.md`).

| Test | Patch | What it shows | Time (4 vCPUs) |
|---|---|---|---|
| `fixes/roms-sed-morph-tiling/run.sh OUTDIR` | roms-sed-morph-tiling | Inlet_test 1x1 vs 1x2 tiles: differ before, bit-identical after | 40 min |
| `fixes/roms-vegetation/run.sh SOURCE OUTDIR` | roms-vegetation | source check; Reef_Ideal_A15_veg: crash before, clean after, zero-gap stop, tau_veg units effect | 1.5 h |
| `fixes/roms-wec-stokes-fixes/run.sh SOURCE OUTDIR` | roms-wec-stokes-fixes | source check of the u and v loops; Inlet_test before vs after | 15 min |
| `fixes/roms-limit-bstress/run.sh OUTDIR` | roms-limit-bstress | preprocessed Fortran of Veg_test, as shipped and `-WET_DRY +LIMIT_BSTRESS` | 15 min |
| `fixes/roms-wetdry-stokes/run.sh OUTDIR [MINUTES]` | roms-wetdry-stokes | Reef_Ideal_A15 with vs without WET_DRY: 0.24 m/s apart before, 6e-5 after; executables without WET_DRY identical | 15 min + runs |
| `fixes/roms-restart-wec/run.sh OUTDIR [TOTAL RST]` | roms-restart-wec | 60 min straight vs 30 + 30 restarted, A15 with canopy, with a river and bare | 20 min + runs |
| `fixes/swan-nc-crash/run.sh OUTDIR` | swan-nc-crash | Inlet_test with SWAN bounds-checked: stops before, clean after | 15 min |
| `fixes/swan-stop-on-input-errors/run.sh OUTDIR` | swan-stop-on-input-errors | rejected SWAN request: carries on before, clean stop after | 15 min |
| `fixes/swan-output-fixes/run.sh OUTDIR` | swan-output-fixes | Inlet_test with points between grid points, NetCDF TABLE and BLOCK, 1 and 2 SWAN | 20 min |
| `fixes/swan-vegetation-fixes/run.sh SOURCE OUTDIR` | swan-vegetation-fixes | source check; Veg_test with VEGETATION 3, submerged and emergent plants | 25 min |
| `fixes/swan-periodic-fixes/run.sh SOURCE OUTDIR` | swan-periodic-fixes | source check; standalone periodic reef (cases/Swan_Periodic_Test), 1 and 4 SWAN processes | 25 min |
| `fixes/swan-periodic-fixes/run_a15_coupled.sh SOURCE OUTDIR` | swan-periodic-fixes (`periodic_coupled_stokes`) | coupled periodic Reef_Ideal_A15 with and without the change: blow-up before, clean after | 40 min |
| `fixes/swan-halo-hang/run.sh OUTDIR [TIMEOUT_S]` | swan-halo-hang | periodic channel with 1100-point rows on 2 SWAN processes: hangs before, finishes after | 15 min |
| `fixes/swan-exact-restart/run.sh OUTDIR` | swan-exact-restart | standalone SWAN, straight vs restarted, binary and text restart files | 15 min |
| `improvements/swan-netcdf-output/run.sh OUTDIR` | swan-netcdf-output | Inlet_test, each quantity as .nc and .mat: run bit-identical, .nc exact after, 18 more quantities | 10 min |

## Test cases

`cases/` holds cases used by several tests: `Reef_Ideal_A15` and
`Reef_Ideal_A15_veg` (an idealized fringing reef with a pass, ROMS + SWAN,
periodic; see their READMEs) and `Swan_Periodic_Test` (standalone SWAN).
Tests that run A15 build with two improvements borrowed from later in the
series (`swan-netcdf-output`, `swan-periodic-curvilinear`), which its SWAN
setup needs.

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
| `tools/run_case.sh IMAGE OUTDIR NAME CASE [TI TJ NWAV MINUTES]` | runs a tests/cases case (e.g. Reef_Ideal_A15) |
| `tools/case_inside.sh CASE [...]` | the same, inside a coawst container |
| `tools/variant_patches.sh SOURCE OUTDIR NAME[,NAME]` | a patch folder with SWAN changes left out (for with/without comparisons) |
| `tools/restart_inside.sh CASE TOTAL RST [TI TJ NWAV]` | straight, part1 and restarted part2 of a case in one container (restart tests) |
| `tools/compare_nc.py A.nc B.nc [VAR ...] [--last]` | largest difference per variable, bit-identical or not |

The Python scripts need numpy and netCDF4; the tests use `$PYTHON`
(default `python3`), e.g. `PYTHON=~/venv/bin/python tests/fixes/.../run.sh ...`.
