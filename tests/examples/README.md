# Test: COAWST examples sweep

Do the engine's patches break any of COAWST's own examples? This test builds
every example that ships with COAWST and uses only ROMS and/or SWAN, once as
stock COAWST and twice with the engine's patches, runs all of them, and
compares the outputs file by file.

## The examples

[`examples.tsv`](examples.tsv) lists them (COAWST's `Projects/` at the pinned
commit). Left out: everything that needs WRF, WAVEWATCH III or InWave
(Sandy, JOE_TC, Delilah, Lip, InWave_shoreface, Inlet_test InWave and WW3,
Ducknc ROMS_InWave).

| Example | Models | What it exercises | Run here |
|---|---|---|---|
| Inlet_test Coupled | ROMS + SWAN | tidal inlet, waves (WEC_VF, roller), bottom boundary layer | 12 h (as shipped) |
| Inlet_test DiffGrid | ROMS + SWAN | SWAN on a different grid (coupler interpolation, SCRIP weights) | 12 h (as shipped) |
| Inlet_test Refined | ROMS + SWAN | nested ROMS and SWAN grids (refinement) | 12 h (as shipped) |
| Inlet_test Swanonly | SWAN | nested SWAN grids, SWAN alone | 12 h (as shipped) |
| Rip_current | ROMS + SWAN | rip currents on a barred beach, wetting/drying | 10 min (of 30) |
| Veg_test | ROMS + SWAN | vegetation drag and wave dissipation by plants | 2 h (of 48) |
| Ducknc | ROMS | cross-shore beach with WEC from a wave forcing file | 10 min (as shipped) |
| Estuary_test2 | ROMS | estuary with salinity, GLS mixing | 1 day (of 5) |
| Marsh_test | ROMS | marsh with vegetation, sediment, wetting/drying, analytical waves | 1 day (of 35) |
| Sed_bed_toy | ROMS | sediment bed layers in a 1-D column | 5 days (as shipped) |
| Sed_floc_toy | ROMS | flocculation in a 1-D column | 3 days (as shipped) |
| Trench | ROMS | sediment-filled trench in a current | 500 s (as shipped) |
| Veg_growth_test | ROMS | seagrass growth with estuarine biogeochemistry | 6 h (of 48) |
| Wetdry dam_break | ROMS (2-D) | dam break over a dry bed | 10 s (as shipped) |
| Wetdry slope_chan | ROMS (2-D) | wetting/drying in a sloping channel | 12 h (as shipped) |

Process layouts (in `examples.tsv`) use several ROMS tiles and two SWAN
processes where the grid allows, so tiling and SWAN's parallel output are
exercised too; each layout is the same for the three builds. The long
examples are cut short to keep the sweep cheap.

## The three builds

| Build | Patches | Compiler settings |
|---|---|---|
| `stock` | none: COAWST as shipped | COAWST's (ROMS `-O3 -ffast-math`, SWAN `-O`) |
| `patched` | the whole series ([`build/coawst/patches/series`](../../build/coawst/patches/series)) | COAWST's |
| `engine` | the whole series | the engine's ([build settings](../../build/coawst/patches/2-improvements/build-settings.md)): what users get |

- **stock vs patched** isolates the patches. Same compiler, same flags, so
  any difference is caused by a patch. The fixes are expected to change some
  examples, and each change must be traced to a named patch.
- **patched vs engine** isolates the compiler settings. Different
  optimization changes the last digits, which then grow in a nonlinear model.

## What it does, step by step

`run.sh OUTDIR [NAME ...]` runs four stages (`STAGES`):

1. **build**: 3 images per example (`coawst-ex:<name>-<variant>`), with
   `build/coawst/build.sh --project ...`. A failed build is a result, not a stop.
2. **pack**: copies all binaries and example folders into one image
   (`coawst-ex:sweep`), so one Cloud Batch job can run everything.
3. **run**: [`example_inside.sh`](example_inside.sh) runs each example with
   the three builds in turn, on the same machine. It copies the example's input
   files and edits only:
   - the process layout;
   - the run length;
   - the coupling file's input and weight-file names.

   It records the outcome: finished, blew up, error, failed or timeout. Run
   locally, it goes through the examples one after the other. As a Cloud Batch
   task it takes one example per task (`BATCH_TASK_INDEX`).
4. **compare**: [`compare.py`](compare.py) writes `OUTDIR/results.md`. For each
   pair it lists the output files that are bit-identical, and for the others
   the largest relative difference: the largest |A − B| of a variable over its
   largest |A|. It compares:
   - NetCDF variables;
   - SWAN `.mat` arrays;
   - numbers in SWAN's text tables and spectra.

## Running it

```bash
PYTHON=~/venv/bin/python tests/examples/run.sh OUTDIR
```

The builds take about 2 h on 4 vCPUs (45 builds). Run on this 4-vCPU machine,
the runs take several hours; on Cloud Batch (one task per example,
c2d-standard-8) about half an hour. `STAGES="compare"` re-reads existing runs.

The outputs are what each build produces. They are not validated reference
solutions.

## Last result

Run 2026-11-01 on Cloud Batch (c2d-standard-8 Spot, one task per example),
COAWST at the pinned commit, the whole series. Every example ran to its end
in all three builds: **none fails on stock COAWST v3.9.**

### Stock vs patched: what the patches change

The partial-series builds (`upto-<patch>`, compared one step at a time) name
the patch behind each change. "Main fields" are sea level, currents,
temperature, salinity and wave height (largest |A − B| over the largest |A|).

| Example | Result | Patch, main fields |
|---|---|---|
| Ducknc, Estuary_test2, Sed_bed_toy, Sed_floc_toy, Wetdry dam_break, Wetdry slope_chan | **bit-identical** | |
| Trench | changes | `roms-sed-morph-tiling` only: sea level 0.4 % |
| Marsh_test | changes | `roms-sed-morph-tiling` only: a few cells wet in one build, dry in the other; elsewhere 0.03 % |
| Inlet_test Coupled | changes | `roms-sed-morph-tiling`: ubar 17 % (at a station); `roms-wec-stokes-fixes`: 1.3 % |
| Inlet_test DiffGrid | changes | `roms-sed-morph-tiling`: 0.6 %; `roms-wec-stokes-fixes`: 0.004 % |
| Inlet_test Refined | changes | `roms-sed-morph-tiling`: 0.08 %; `roms-wec-stokes-fixes`: 0.004 % |
| Inlet_test Swanonly | changes | `swan-output-fixes` only, point output: stock left grid corners out of the interpolation to the output point (flags never set), so Hs there was 0.4 % and the wavelength 0.6 % off, and part of the spectrum file was written as NODATA |
| Veg_test | changes | `roms-vegetation`: u 7 %, eddy viscosity 41 %; `roms-wetdry-stokes`: u 0.4 % |
| Veg_growth_test | changes | `roms-vegetation` only: currents 5-7 %, sea level 0.9 %, eddy viscosity 23 %; the biogeochemistry follows the changed mixing (NO3 up to 47 %) |
| Rip_current | changes | `roms-wec-stokes-fixes` and `roms-wetdry-stokes` (ubar/vbar 16-18 %); `swan-force-strip-rows`: `force.mat` had 152 points missing |

Smaller, output-only changes: `swan-output-fixes` (SWAN spectra, below 1e-5
relative, in the coupled Inlet runs), and the restart-file fixes (restart
files only: `Cdwave_veg` in Veg_test, sediment parameters in Inlet_test).
`roms-wec-stokes-fast` changes last digits (1e-7 to 3e-5), except in
Rip_current (below).

### Patched vs engine: what the build settings change

Wave heights agree to about 1e-5. ROMS fields agree to 1e-7 or better in most
examples. Two exceptions grow from last digits to large differences, because
their flow is unstable:

- **Estuary_test2**: the builds agree to 1e-13 for 5 h; the difference then
  grows about tenfold per hour and saturates after about 15 h (u 0.5 m/s of
  1.1, salinity 1.7). Stock vs patched is bit-identical here, so no patch
  affects it.
- **Rip_current**: rip-current eddies; any last-digit change gives 15-20 %
  in the currents after 10 minutes. For this example only "changed or not"
  means something, not the size of a change.

Large relative values in `results.md` for nearly-zero fields (v in 2-D
slices, u in Marsh_test, the 1-D sediment columns) mean nothing.

### Finding: van der A bedload writes unset memory when there is no sand

In Inlet_test DiffGrid and Refined, the output `fd_wbl` (wave boundary layer
friction factor from currents, van der A bedload with
`BEDLOAD_VANDERA_MADSEN_UDELTA`) differed between builds whose code is the
same (the last two partial builds; the patches between them are off), in one
column at the edge between two tiles (5.69 in one build, 0 in the other).
Its values elsewhere, about 1e-17 or negative, are impossible for this
friction factor (0, or at least 1e-14).

**Cause (stock COAWST v3.9).** These two examples carry mud only
(`NCS = 1`, `NNS = 0`). In `sed_bedload_vandera.F` the loop that computes
the van der A quantities runs over sand classes only (`DO ised=NCS+1,NST`),
so here it never runs, but the routine still copies its local work arrays
(`fd_wbll`, `ursell_nol`, `RR_asymwavel`, `beta_asymwavel`, `ucrest_rl`,
`utrough_rl`, `T_crestl`, `T_troughl`, and `ksd_wbll` with
`BEDLOAD_VANDERA_DIRECT_UDELTA`) into the global fields. They hold whatever
was in each process's memory; the change at the tile edge is two MPI
processes with different leftovers.

**Proof.** Stock DiffGrid, ROMS 2x2 + 2 SWAN, 2 h, built once as usual and
once with `ROMS_FFLAGS_EXTRA="-finit-real=snan -fcheck=bounds"` (unset local
memory filled with NaN, array bounds checked): no bounds error; `fd_wbl` is
NaN at all 5333 water points and is the only NaN field in the history file.

**Effect.** Output only: these fields are only written to files (and
`ksd` with `BEDLOAD_VANDERA_DIRECT_UDELTA` is not read back), so the model
state does not depend on them, as the bit-identical runs show. Any run with
`BEDLOAD_VANDERA` and no sand class writes meaningless van der A
diagnostics. A fix would set those arrays (e.g. to zero) before the loop. To
report upstream.

### Cost

About $3.40: the sweep 9.1 machine-hours, the partial-series runs 14.7
machine-hours (c2d-standard-8 Spot, about $0.14/h).
