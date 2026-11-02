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

prints `IDENTICAL: <n> files`, or the files that differ. Each differing file is
marked `comments` (the same once comments are removed) or `code`, and its
differing code lines are shown ([`code_diff.py`](same_source/code_diff.py)). This
also compares this series with another project's copy of the same patches.

## Automated checks

The scripts that GitHub Actions run (`.github/workflows/`); each prints PASS
or FAIL and runs the same way on any machine.

| Script | What it checks | When (Actions) | Time |
|---|---|---|---|
| `ci/series_check.sh [REF]` | every patch in `series` exists and has its document, every patch file is in `series`, and the series applies to COAWST at `REF` (default: the pinned commit; `main` = upstream's latest) | pinned: every push and pull request; `main`: weekly | 1 min + download |
| `romspath/periodic-channel/run.sh OUTDIR` | ROMSPath: every commit of the fork and the image on a periodic channel with an exact answer ([README](romspath/periodic-channel/README.md)) | every push and pull request | 1 min |
| `ci/inlet_smoke.sh OUTDIR [HOURS]` | the engine image of Inlet_test builds and runs coupled (ROMS 1x2 + 1 SWAN) for an hour without NaN, and writes compressed NetCDF-4 | pull requests that change the image or `tests/tools/`, by hand, weekly | 13 min on GitHub runners |
| `ci/romspath_upstream.sh` | upstream ROMSPath's new commits, and whether the fork's commits replay onto them | weekly | 1 min |

The weekly checks against upstream's latest code do not test the engine
itself, which builds pinned commits. They warn when a COAWST or ROMSPath update
would need work, and say where.

## COAWST's examples

| Test | What it checks | Time |
|---|---|---|
| `examples/run.sh OUTDIR [NAME ...]` | every COAWST example that uses only ROMS and/or SWAN (15), built as stock COAWST, with the patches and COAWST's flags, and as the engine builds it; runs all three and compares the outputs ([README](examples/README.md)) | 2 h of builds (4 vCPUs) + runs |

## Tests of the patches

One folder per patch under `fixes/`, `improvements/` and `experimental/`,
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
| `fixes/roms-restart-wec/run.sh OUTDIR [TOTAL RST]` | roms-restart-wec | 60 min straight vs 30 + 30 restarted, A15 with canopy, with a river and bare; 4 restart records in one file | 20 min + runs |
| `fixes/roms-restart-step-count/run.sh OUTDIR` | roms-restart-step-count | Reef_Ideal_A15 with DSTART far from its start: restart wrong before, stops with a message after; normal case bit-identical | 10 min + runs |
| `fixes/roms-vandera-no-sand/run.sh OUTDIR [MINUTES]` | roms-vandera-no-sand | Inlet_test DiffGrid (mud only) with unset memory as NaN: fd_wbl NaN before, zero after, rest bit-identical; Inlet_test Coupled (sand) bit-identical | 25 min |
| `fixes/roms-prsgrd40-wetdry/run.sh OUTDIR [MINUTES]` | roms-prsgrd40-wetdry | Reef_Ideal_A15 with `PJ_GRADP`: with `WET_DRY` no compile before, compiles and runs after; without `WET_DRY` identical executables | 20 min + run |
| `fixes/swan-nc-crash/run.sh OUTDIR` | swan-nc-crash | Inlet_test with SWAN bounds-checked: stops before, clean after | 15 min |
| `fixes/swan-stop-on-input-errors/run.sh OUTDIR` | swan-stop-on-input-errors | rejected SWAN request: carries on before, clean stop after | 15 min |
| `fixes/swan-output-fixes/run.sh OUTDIR` | swan-output-fixes | Inlet_test with points between grid points, NetCDF TABLE and BLOCK, 1 and 2 SWAN | 20 min |
| `fixes/swan-force-strip-rows/run.sh OUTDIR` | swan-force-strip-rows | Inlet_test FORCE on 1, 2, 3 SWAN processes: strip-boundary columns missing before, identical after; other output and ROMS bit-identical | 25 min |
| `fixes/swan-vegetation-fixes/run.sh SOURCE OUTDIR` | swan-vegetation-fixes | source check; Veg_test with VEGETATION 3, submerged and emergent plants | 25 min |
| `fixes/swan-periodic-fixes/run.sh SOURCE OUTDIR` | swan-periodic-fixes | source check; standalone periodic reef (cases/Swan_Periodic_Test), 1 and 4 SWAN processes | 25 min |
| `fixes/swan-periodic-fixes/run_a15_coupled.sh SOURCE OUTDIR` | swan-periodic-fixes (`periodic_coupled_stokes`) | coupled periodic Reef_Ideal_A15 with and without the change: blow-up before, clean after | 40 min |
| `fixes/swan-halo-hang/run.sh OUTDIR [TIMEOUT_S]` | swan-halo-hang | periodic channel with 1100-point rows on 2 SWAN processes: hangs before, finishes after | 15 min |
| `fixes/swan-exact-restart/run.sh OUTDIR` | swan-exact-restart | standalone SWAN, straight vs restarted, binary and text restart files | 15 min |
| `improvements/swan-netcdf-output/run.sh OUTDIR` | swan-netcdf-output | Inlet_test, each quantity as .nc and .mat: run bit-identical, .nc exact after, 18 more quantities | 10 min |
| `improvements/swan-netcdf4-compression/run.sh OUTDIR` | swan-netcdf4-compression | Inlet_test BLOCK, TABLE and SPECOUT .nc, three builds: identical values, NetCDF-4 + deflate with the options | 15 min |
| `improvements/swan-periodic-curvilinear/run.sh OUTDIR` | swan-periodic-curvilinear | standalone periodic SWAN on curvilinear grids: same as regular, seam through the pass, processes, output search, refused before | 20 min |
| `improvements/roms-wec-stokes-fast/run.sh OUTDIR [MINUTES]` | roms-wec-stokes-fast | Reef_Ideal_A15 with PROFILE: fields at rounding level, WEC kernel CPU time | 10 min + runs |
| `improvements/build-settings/run.sh OUTDIR` | build settings | Inlet_test SPECOUT on 1 vs 2 SWAN; A15 stock vs engine flags: differences, repeats, speed | 40 min + runs |
| `experimental/options-off/run.sh OUTDIR` | all of 3-experimental | options off: same preprocessed Fortran with and without the patches (Inlet_test, A15_veg, A15 + WET_DRY, Circle_Island) | 1 h |
| `experimental/roms-step2d-fb/run.sh OUTDIR [MINUTES]` | roms-step2d-fb | AB3-AM4 vs LF-AM3 vs a 4x-smaller-step reference on A15 and Circle_Island; PROFILE timing | 20 min + runs |
| `experimental/roms-veg-implicit/run.sh OUTDIR [MINUTES]` | roms-veg-implicit | A15_veg patchy canopy: explicit blows up at DT 6 s, implicit vs explicit DT 3 s | 10 min + runs |
| `experimental/roms-bstress-implicit/run.sh OUTDIR [MINUTES]` | roms-bstress-implicit | A15 and Circle_Island with and without the option (a record) | 20 min + runs |
| `experimental/roms-bstress-implicit/thin_crest.sh OUTDIR [MINUTES] [GRIDS]` | roms-bstress-implicit | thin-crest A15 variants: capped, uncapped and implicit stress compared | 15 min + 3 runs per grid |
| `experimental/wec-break-uniform/run.sh OUTDIR [MINUTES]` | wec-break-uniform | A15 breaking acceleration profile, default vs uniform | 10 min + runs |
| `improvements/swan-closed-ring/run.sh OUTDIR [MINUTES]` | swan-closed-ring | Circle_Island O-grid: refused before; coupler map in both directions with 1, 2, 3 SWAN; layouts; seam moved; waves from all sides; A15 unchanged | 20 min + runs |

## Test cases

`cases/` holds cases used by several tests: `Reef_Ideal_A15` and
`Reef_Ideal_A15_veg` (an idealized fringing reef with a pass, ROMS + SWAN,
periodic; see their READMEs), `Circle_Island` (a round island with a
fringing reef on a closed O-grid, ROMS + SWAN; written by its `make_case.py`)
and `Swan_Periodic_Test` (standalone SWAN).
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
