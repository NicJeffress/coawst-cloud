# Building and running the COAWST image

This folder turns COAWST into a container image: a self-contained Linux
system with the compiled coupled model (`coawstM`) and everything it needs at
run time (OpenMPI, NetCDF). The same image runs on a laptop with Docker, on a
cluster with Apptainer/Singularity, or on Google Cloud.

| File | What it is |
|---|---|
| [`Dockerfile`](Dockerfile) | The recipe: fetch COAWST at a pinned commit, build MCT, apply the patch series, set the build settings, compile your case, copy the result into a small run image |
| [`build.sh`](build.sh) | Puts the build context together (Dockerfile, patches, your case) in a temporary folder and runs `docker build` |
| [`apply_series.sh`](apply_series.sh) | Applies `patches/series` in order; also used by the tests, so a series is applied the same way everywhere |
| [`patches/`](patches/README.md) | The patch series, one document per patch |
| `vendor/` | Optional: a tarball of the COAWST commit, used instead of GitHub (see [Offline builds](#offline-builds)) |

## What you need

- **Docker** (Linux, or Docker Desktop on macOS/Windows), with about 10 GB of
  free disk for the build stage and its cache.
- **An x86-64 machine.** The image is compiled for `x86-64-v3` (AVX2 and FMA),
  which every Intel and AMD processor from about 2015 on has, and every
  current cloud machine. On an older CPU, or on ARM (Apple silicon), see
  `ARCH_FLAGS` below.
- **Time:** the first build downloads COAWST (about 500 MB) and compiles MCT,
  roughly 10 minutes on 4 cores. Later builds reuse that cached work and take
  about 3-5 minutes (the case-specific part: ROMS and SWAN).

## Building

```bash
build/coawst/build.sh                                    # COAWST's Inlet_test (coupled), all patches
build/coawst/build.sh --project Projects/Veg_test --app VEG_TEST
                                                         # another example shipped with COAWST
build/coawst/build.sh --case ~/cases/MyReef --app MY_REEF
                                                         # your own case
build/coawst/build.sh --case ~/cases/MyReef --app MY_REEF -- --build-arg CPP_OPTIONS="+VEG_DRAG_IMPLICIT"
                                                         # with an extra cpp option
```

The image is tagged `coawst:<application in lower case>` (e.g.
`coawst:my_reef`); `--tag NAME` chooses another name.

### Your own case

A case is a folder with:

| File | Needed for | Notes |
|---|---|---|
| `<app in lower case>.h` | compiling | the case header with the cpp options (`#define UV_VIS2`, `#define SWAN_MODEL`, ...); the name must match `--app` |
| `ana_*.h` | compiling, if the header uses analytical functions | found in the case folder (COAWST's `MY_ANALYTICAL_DIR`) |
| `coupling.in`, `ocean.in`, `swan.in` | running | read at run time, not compiled in; can be changed without rebuilding |
| grids, initial and forcing NetCDF, SWAN `.bot`/`.grd` files | running | copied into the image with the folder if they are in it; or keep them outside and mount them at run time (better for large files) |

The whole folder is copied to `/opt/coawst/Projects/<folder name>` in the
image. Everything set by a `#define` is fixed in the image; everything in the
`.in` files can change from run to run. An ensemble that varies only `.in`
files and input NetCDF (forcing, bathymetry, parameters) therefore shares one
image.

### Build options

`build.sh` options:

| Option | Meaning |
|---|---|
| `--case DIR --app NAME` | build your case folder `DIR`, application flag `NAME` |
| `--project Projects/X --app NAME` | build a case that ships with COAWST |
| `--tag TAG` | image name (default `coawst:<app in lower case>`) |
| `--series FILE` / `--series none` | apply another series file (paths relative to `patches/`), or no patches |
| `--patch-dir DIR` | use another patch folder (tests that leave one change out) |

Build arguments, passed after `--` as `--build-arg NAME=VALUE`:

| Argument | Default | Meaning |
|---|---|---|
| `COAWST_REF` | the pinned commit in the Dockerfile | COAWST commit to build |
| `SERIES` | `series` | patch series file; `none` = no patches (`build.sh --series none` sets it) |
| `BUILD_SETTINGS` | `engine` | `engine`: SWAN `-O3`, no `-ffast-math`, `SWAN_SINGLESPEC` off, compressed output ([build settings](patches/2-improvements/build-settings.md)); `stock`: COAWST's own choices |
| `ARCH_FLAGS` | `-march=x86-64-v3 -g` | CPU target and debug flags for ROMS and SWAN; e.g. `-march=x86-64 -g` for old CPUs, `-g` alone on ARM |
| `OUTPUT_OPTIONS` | `+OUT_NETCDF4 +DEFLATE` (engine), nothing (stock) | output format cpp options; `""` gives classic NetCDF files |
| `CPP_OPTIONS` | none | `+X` adds `#define X`, `-X` adds `#undef X` at the end of the case header, after `OUTPUT_OPTIONS`; e.g. `"+STEP2D_FB_AB3_AM4 -UV_VIS2"` |
| `NJOBS` | 4 | parallel compile jobs |
| `ROMS_FFLAGS_EXTRA`, `SWAN_FFLAGS_EXTRA` | none | extra compiler flags for checks, e.g. `-fcheck=bounds` or `-finit-real=snan` |
| `RUNTIME_PKGS` | none | extra Ubuntu packages in the run image (e.g. `libasan8` for a memory-checking build) |

COAWST exactly as shipped, for comparison:

```bash
build/coawst/build.sh --series none --tag coawst:stock -- --build-arg BUILD_SETTINGS=stock
```

### What is in the image

| Path | What |
|---|---|
| `/opt/coawst/coawstM` | the coupled executable (on the `PATH`) |
| `/opt/coawst/COAWST_COMMIT` | the COAWST commit it was built from |
| `/opt/coawst/PATCHES_APPLIED` | the patches applied, in order |
| `/opt/coawst/build/build.log`, `build_coawst.sh` | the full compile log and the build script used |
| `/opt/coawst/Projects/<case>/` | the case folder (header, `.in` files, any input files in it) |
| `/opt/coawst/ROMS/External/varinfo.yaml` | ROMS's variable metadata, read at start-up |

`COAWST_COMMIT` and `PATCHES_APPLIED` let anyone find out later exactly what
code produced a set of results; the run scripts copy them next to the output.

## Running

ROMS and SWAN run as separate groups of MPI processes inside one `mpirun`:

- ROMS uses `NtileI x NtileJ` processes (in `ocean.in`);
- SWAN uses `NnodesWAV` processes (in `coupling.in`);
- `coupling.in` also needs `NnodesOCN = NtileI x NtileJ`;
- `mpirun -np` takes the sum.

For example, ROMS 2 x 2 tiles plus 2 SWAN processes gives
`NnodesOCN = 4`, `NnodesWAV = 2`, `mpirun -np 6`.

The model runs in a writable folder that holds (or links to) its `.in` files
and receives the output:

```bash
mkdir run && cd run
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" -w /work coawst:my_reef bash -c '
    cp -r /opt/coawst/Projects/MyReef/. .        # the case files, to edit and run here
    mpirun --use-hwthread-cpus --bind-to none -np 6 coawstM coupling.in > log.txt 2>&1'
```

Notes:

- **`--use-hwthread-cpus`** lets OpenMPI count hyperthreads as slots. Cloud
  "vCPUs" are hyperthreads (two per physical core), so 4 processes fit on a 4-vCPU
  machine. **`--bind-to none`** leaves process placement to the operating
  system, which was faster for coupled runs on cloud machines.
- **Root:** containers often run as root, which OpenMPI refuses by default.
  The image sets `OMPI_ALLOW_RUN_AS_ROOT`, so it also works where it cannot be
  avoided (Cloud Batch).
- **Paths in the `.in` files** are read relative to the run folder. Cases
  whose files name each other without a path (like the test cases in
  `tests/cases`) run as above. COAWST's own examples use paths such as
  `Projects/Inlet_test/Coupled/...`. For those, link `/opt/coawst/Projects`
  into the run folder; [`tests/tools/inlet_inside.sh`](../../tests/tools/inlet_inside.sh)
  does that.
- **Different ROMS and SWAN grids:** COAWST computes interpolation weights at
  start-up and writes them to the file named by `SCRIP_COAWST_NAME` in
  `coupling.in`. Give it a name in the run folder; a path into the image's
  read-only folders fails with "Permission denied".
- **Ready-made runners:**
  - [`tests/tools/run_inlet.sh`](../../tests/tools/run_inlet.sh) runs Inlet_test;
  - [`tests/tools/run_case.sh`](../../tests/tools/run_case.sh) runs a
    `tests/cases` case, with tiles, SWAN processes, run length, time step
    and output interval as arguments.

### Apptainer / Singularity (clusters)

HPC clusters usually run Apptainer rather than Docker. Convert the image once:

```bash
apptainer build coawst_my_reef.sif docker-daemon://coawst:my_reef     # on a machine with Docker
apptainer exec --bind "$PWD" coawst_my_reef.sif \
    mpirun --use-hwthread-cpus --bind-to none -np 6 coawstM coupling.in
```

This runs on one node with the image's own OpenMPI. To run across several
nodes, the image's MPI has to work with the cluster's interconnect; ask your
cluster's support which approach they use.

### Output format

By default ROMS writes **compressed NetCDF-4**:
- `OUT_NETCDF4`: NetCDF-4/HDF5 files;
- `DEFLATE`: lossless compression.

So do SWAN's `.nc` files
([swan-netcdf4-compression](patches/2-improvements/swan-netcdf4-compression.md)).
The values are identical to classic files and the files are 2-4 times
smaller, at a cost of about 1-2 % of run time. Python (netCDF4, xarray), MATLAB,
ncview and NCO read them like any NetCDF file. For classic NetCDF-3 files,
build with `-- --build-arg OUTPUT_OPTIONS=""`.

## Reproducibility

- **Pinned source.** COAWST is built at one commit (`COAWST_REF`) with a fixed
  patch series; Ubuntu 24.04's compilers and libraries.
- **No `-ffast-math`.** Results do not depend on the compiler's freedom to
  reorder arithmetic. The same image, MPI layout and tiling give bit-identical
  results run after run, and on Intel and AMD machines (tested on the
  idealized reef).
- **Different layouts are not bit-identical.** Changing the number of ROMS
  tiles or SWAN processes changes the order of sums, so the last digits
  differ (except where a fix made a result layout-independent, e.g.
  [roms-sed-morph-tiling](patches/1-fixes/roms-sed-morph-tiling.md)). Keep
  the layout fixed within an ensemble.
- **Exact restarts.** With [roms-restart-wec](patches/1-fixes/roms-restart-wec.md)
  and [swan-exact-restart](patches/1-fixes/swan-exact-restart.md), a run
  stopped and restarted from its restart files continues exactly as if it had
  not stopped. This is what lets long runs use cheap, interruptible (Spot)
  machines.

## Offline builds

The build fetches COAWST from GitHub. If GitHub is unreachable, or to be
independent of it, put a tarball of the commit in `vendor/` as
`COAWST-<COAWST_REF>.tar.gz`, with one top-level folder, e.g.
`git archive --prefix=COAWST/ <COAWST_REF> | gzip > COAWST-<COAWST_REF>.tar.gz`
in a clone of COAWST. The Dockerfile uses it instead
and records `archive vendor/...` in `COAWST_COMMIT`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `There are not enough slots available` | more processes than OpenMPI counts; add `--use-hwthread-cpus`, or `--oversubscribe` on a small machine (slow) |
| `Illegal instruction` at start-up | the CPU lacks AVX2; rebuild with `--build-arg ARCH_FLAGS="-march=x86-64 -g"` |
| `Error in netCDF: Permission denied` at start-up | the coupler is writing its weights file into the image; set `SCRIP_COAWST_NAME` in `coupling.in` to a file in the run folder |
| `ROMS/TOMS - Blows up` | the model went unstable; usually a time step too long for the grid (`DT`, `NDTFAST`), or a bad input file |
| the build stops at `test -f ...h` | the header name must be the application flag in lower case, in the case folder |
| SWAN stops with an input error | the run stops cleanly with SWAN's message ([swan-stop-on-input-errors](patches/1-fixes/swan-stop-on-input-errors.md)); see SWAN's `PRINT` file(s) in the run folder |
| spectral output (`SPECOUT`) truncated with several SWAN processes | `SWAN_SINGLESPEC` is on; the engine settings turn it off, `BUILD_SETTINGS=stock` does not |
