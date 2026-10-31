# Test: swan-netcdf-output

Checks [`2-improvements/swan-netcdf-output.patch`](../../../build/coawst/patches/2-improvements/swan-netcdf-output.md):
SWAN writes every 2-D output quantity as NetCDF at full precision, and
nothing else in the run changes.

## The idea

SWAN can write the same field in two formats: NetCDF (`.nc`), which goes
through SWAN's NetCDF name and type tables (what the patch changes), and
MATLAB (`.mat`), which does not. So the `.mat` file of the same run is an
exact reference for the `.nc` file. The test asks for each quantity in both
formats and compares them, before and after the patch. Being an improvement,
the patch must also leave the model itself alone: the same run before and
after must give bit-identical waves and currents.

## What it does, step by step

1. **Builds** COAWST's coupled Inlet_test twice: with the series up to the
   patch (`before`, all the fixes) and with the patch (`after`).
2. **Runs** four 1-hour runs on the machine (ROMS 1 tile + 1 SWAN process,
   about a minute each), adding `BLOCK` requests to SWAN's input
   (`SWANSED`), every 30 min, for each quantity both as `n_<q>.nc` and as
   `m_<q>.mat`:

   | Run | Image | Quantities |
   |---|---|---|
   | `before-same` | before | the 7 that stock SWAN accepts as `.nc`: DEPTH, WATLEV, BOTLEV, VEL, HSIGN, RTP, UBOT |
   | `after-same` | after | the same 7 |
   | `after-all` | after | the 7 and 18 added by the patch: FRCOEF, DISSIP, TMBOT, QB, TRANSP, FORCE, STEEPNESS, PER, RPER, URSELL, DISBOT, DISSURF, DISWCAP, GENERAT, REDIST, PROPAGAT, RADSTR, TDIR |
   | `before-new` | before | DISSIP as `.nc` only |

3. **Checks** (`check.py`):
   - *unchanged*: `before-same` and `after-same` have bit-identical `.mat`
     files (30 files, the case's own and the test's) and a bit-identical
     ROMS history;
   - *precision*: for each of the 7, the `.nc` values against the `.mat`
     values of the same run. Before the patch, quantities stored as packed
     16-bit integers differ by up to half a packing step; after it, all are
     equal, with the same missing (land) points, and none is packed;
   - *new quantities*: in `after-all`, each of the 18 added `.nc` files is
     float and equal to its `.mat` file;
   - *refused*: `before-new`'s SWAN print file says "netCDF output not
     allowed" (and the run stopped, because of `swan-stop-on-input-errors`).
4. **Plots** (`plot_precision.py`) the figure in the patch document.

## Running it

```bash
PYTHON=~/venv/bin/python tests/improvements/swan-netcdf-output/run.sh OUTDIR
```

About 10 min on 4 vCPUs (two builds and four short runs). Needs Docker and
Python with numpy, scipy, netCDF4 and matplotlib.

## Reading the output

```
ok  precision hsign : before packed, max |nc - mat| 3.82e-04; after float, 0.00e+00
```

Hs in the stock `.nc` file was stored as a packed 16-bit integer and was up
to 0.38 mm off; with the patch it is a float equal to the `.mat` value.
"before float" (depth, bottom level) means stock SWAN already stored that
quantity as a float.

## Last result

2026-10-31, control VM: PASS. 30 `.mat` files and the ROMS history
bit-identical before and after; stock `.nc` off by up to 0.38 mm (Hs),
0.23 mm (water level), 0.31 mm/s (currents); with the patch all 25
quantities equal to `.mat`.
