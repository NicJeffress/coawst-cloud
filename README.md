# coawst-cloud

**COAWST (ROMS + SWAN) and ROMSPath in containers, with every change documented
and tested, built for running ensembles of coastal ocean simulations on any
machine and on Google Cloud.**

> **Status: pre-release.** The patched COAWST build and its tests, the
> ROMSPath build, and the automated checks are complete. The Cloud Batch
> launcher (`launch/`) is still to come. Nothing here has been reported to
> the COAWST developers yet.

## Contents

- [What this is](#what-this-is)
- [Why: what changes compared with COAWST as shipped](#why-what-changes-compared-with-coawst-as-shipped)
- [Quick start](#quick-start)
- [Your own case](#your-own-case)
- [The COAWST patches](#the-coawst-patches)
- [ROMSPath (particle tracking)](#romspath-particle-tracking)
- [Tests](#tests)
- [Reproducibility and provenance](#reproducibility-and-provenance)
- [Repository layout](#repository-layout)
- [Roadmap](#roadmap)
- [Licenses and citation](#licenses-and-citation)

## What this is

[COAWST](https://github.com/DOI-USGS/COAWST) (Coupled Ocean-Atmosphere-Wave-
Sediment Transport, USGS) couples the ROMS ocean model with the SWAN wave
model (and WRF, WAVEWATCH III, sediment, vegetation). It is powerful, but
building it is laborious, and some of its parts have bugs that matter for
nearshore work: reefs, beaches, inlets, vegetated shores.

This repository gives you:

1. **A container image of COAWST** (ROMS + SWAN coupled through MCT; no WRF or
   WAVEWATCH III). It is built from the public COAWST repository at a pinned
   commit, plus a series of 26 patches. The image runs the same way on a
   laptop (Docker), a cluster (Apptainer) or the cloud. Your case's cpp
   options are compiled in; `.in` files and input NetCDF are read at run time,
   so one image serves a whole ensemble.
2. **A documented, tested patch series.** Every change has its own document
   (what was wrong, the code before and after, the evidence, the limits) and
   its own test, which shows the problem without the patch and its absence
   with it. The patches are grouped by how well established they are:
   - fixes;
   - improvements;
   - experimental options, which are off unless you switch them on.
3. **A ROMSPath image** for offline particle tracking on ROMS output, built
   from a [fork](https://github.com/NicJeffress/ROMSPath) that adds periodic
   boundaries and fixes timing and placement bugs.
4. **Tests and automated checks**:
   - before/after tests for each patch;
   - COAWST's own examples, built three ways and compared;
   - checks that run on every change and weekly against upstream.

It grew out of running ensembles of idealized reef simulations (about
200 x 200 grid points, a week of simulated time, up to ~100 runs at once) on
Google Cloud, where each run has to work unattended, restart exactly after an
interruption, and give the same answer on any machine.

## Why: what changes compared with COAWST as shipped

The most consequential fixes, for someone deciding whether this matters to
them. Each links to its full document.

| If you use... | COAWST v3.9 as shipped | With this repository |
|---|---|---|
| Sediment morphology (`SED_MORPH`) on several MPI tiles | results depend on the tiling (halo bugs) | [same results for any tiling](build/coawst/patches/1-fixes/roms-sed-morph-tiling.md) |
| ROMS vegetation | crash with periodic boundaries; division by zero when plants cover the bed; the canopy turbulence time scale in the wrong units; wrong drag average at v points | [fixed](build/coawst/patches/1-fixes/roms-vegetation.md) (canopy eddy viscosity about 10 % lower) |
| Wave forcing (`WEC_VF`) with `WET_DRY` | Stokes transport dropped towards -x and -y in the first barotropic sub-step: up to 0.24 m/s error even where nothing dries | [fixed](build/coawst/patches/1-fixes/roms-wetdry-stokes.md) |
| Spectral Stokes drift (`SPECTRUM_STOKES`) | the u-point loop was not the mirror of the v-point loop | [fixed](build/coawst/patches/1-fixes/roms-wec-stokes-fixes.md), and [3x fewer hyperbolic functions](build/coawst/patches/2-improvements/roms-wec-stokes-fast.md) |
| Restarts with waves | restarted runs drift away from straight runs (missing fields in ROMS and SWAN restart files) | [exact restarts](build/coawst/patches/1-fixes/roms-restart-wec.md), so long runs can use cheap interruptible machines |
| SWAN with several processes | NetCDF output with wrong coordinates or missing points; `FORCE` missing a row at every process boundary; a deadlock on long grid rows; spectral output truncated (`SWAN_SINGLESPEC`) | [fixed](build/coawst/patches/README.md#1-fixes) |
| SWAN vegetation (`VEGETATION 3`) | flexible plants always rigid; Cd stuck at 1.95 for emergent plants; plant inputs read from the wrong grids | [fixed](build/coawst/patches/1-fixes/swan-vegetation-fixes.md) |
| Periodic domains (`EW_PERIODIC` with SWAN `REPEATING`) | SWAN output and Stokes fields shifted; crashes on several processes; curvilinear periodic grids refused | [fixed](build/coawst/patches/1-fixes/swan-periodic-fixes.md), [curvilinear](build/coawst/patches/2-improvements/swan-periodic-curvilinear.md) and [closed O-grids round an island](build/coawst/patches/2-improvements/swan-closed-ring.md) supported |
| SWAN NetCDF output | most quantities refused as NetCDF, others stored as 16-bit integers (Hs in 0.76 mm steps); never compressed | [every 2-D quantity as 32-bit floats](build/coawst/patches/2-improvements/swan-netcdf-output.md), [compressed](build/coawst/patches/2-improvements/swan-netcdf4-compression.md) |
| Speed | SWAN compiled at `-O1`, ROMS with `-ffast-math` | SWAN `-O3`, no `-ffast-math`: [coupled idealized reef 1.7x faster](build/coawst/patches/2-improvements/build-settings.md), and reproducible |

Against COAWST's own 15 examples that use only ROMS and/or SWAN, none fails on
stock v3.9. Six give bit-identical results with the patches; in the other nine,
every difference is traced to a named patch
([examples sweep](tests/examples/README.md)).

## Quick start

You need Docker on an x86-64 machine, about 10 GB of disk, and 4 cores.

```bash
git clone https://github.com/NicJeffress/coawst-cloud.git
cd coawst-cloud

build/coawst/build.sh                        # COAWST's Inlet_test, all patches: image coawst:inlet_test
                                             # (first build ~10 min, later ones ~3-5 min)
tests/tools/run_inlet.sh coawst:inlet_test ~/runs inlet 1 2 1 1
                                             # ROMS on 1x2 tiles + 1 SWAN process, 1 simulated hour
ls ~/runs/inlet                              # ROMS and SWAN output, log.txt, image_info.txt
```

`image_info.txt` records the COAWST commit, the patches and the layout. The
output is compressed NetCDF-4; open it with Python (netCDF4, xarray), MATLAB,
ncview or any NetCDF tool.

To build COAWST exactly as shipped, for comparison:

```bash
build/coawst/build.sh --series none --tag coawst:stock -- --build-arg BUILD_SETTINGS=stock
```

## Your own case

```bash
build/coawst/build.sh --case ~/cases/MyReef --app MY_REEF
```

builds the case folder `~/cases/MyReef` into the image `coawst:my_reef`. The
folder holds:
- the case header `my_reef.h`, with the cpp options;
- any `ana_*.h` files;
- the `.in` files;
- optionally, the input files.

Then run it in a writable folder:

```bash
mkdir run && cd run
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" -w /work coawst:my_reef bash -c '
    cp -r /opt/coawst/Projects/MyReef/. .
    mpirun --use-hwthread-cpus --bind-to none -np 6 coawstM coupling.in > log.txt 2>&1'
```

Here `-np 6` is ROMS's `NtileI x NtileJ` plus SWAN's `NnodesWAV`, e.g. 2 x 2
tiles + 2 SWAN processes.

Common adjustments, as build arguments after `--`:

| You want | Add |
|---|---|
| an extra cpp option, or one of the experimental schemes | `--build-arg CPP_OPTIONS="+VEG_DRAG_IMPLICIT"` (`+X` defines, `-X` undefines) |
| classic NetCDF-3 output | `--build-arg OUTPUT_OPTIONS=""` |
| a build for an old CPU without AVX2 | `--build-arg ARCH_FLAGS="-march=x86-64 -g"` |
| COAWST's own compiler flags | `--build-arg BUILD_SETTINGS=stock` |

The [build and run guide](build/coawst/README.md) has every option, the
image's layout, Apptainer for clusters, MPI layouts and troubleshooting.

## The COAWST patches

26 patches, applied in the order of
[`build/coawst/patches/series`](build/coawst/patches/series), plus build
settings. The [patch index](build/coawst/patches/README.md) has the full
table; each patch has a document next to it with a status card (type, does it
change results, default, evidence, test, upstream status), the bug, the code
before and after, and its limits.

| Tier | Patches | What it means | What its test must show |
|---|---|---|---|
| **fixes** | 17 | COAWST did something wrong | fails without the patch, passes with it |
| **improvements** | 5 + build settings | no change to the physics, or a new capability | results unchanged (bit-identical or rounding level) |
| **experimental** | 4 | off unless their cpp option is defined | build unchanged with the option off; an honest list of what has been checked |

**Fixes**:
- ROMS:
  - [sediment morphology on several tiles](build/coawst/patches/1-fixes/roms-sed-morph-tiling.md);
  - [vegetation](build/coawst/patches/1-fixes/roms-vegetation.md);
  - [spectral Stokes drift](build/coawst/patches/1-fixes/roms-wec-stokes-fixes.md);
  - [`LIMIT_BSTRESS` tied to the wrong option](build/coawst/patches/1-fixes/roms-limit-bstress.md);
  - [Stokes transport with `WET_DRY`](build/coawst/patches/1-fixes/roms-wetdry-stokes.md);
  - [exact restarts with waves, rivers, GLS and sediment](build/coawst/patches/1-fixes/roms-restart-wec.md);
  - [step-counter overflow on restart](build/coawst/patches/1-fixes/roms-restart-step-count.md);
  - [van der A bedload output without sand](build/coawst/patches/1-fixes/roms-vandera-no-sand.md);
  - [the `PJ_GRADP` pressure gradient with `WET_DRY`](build/coawst/patches/1-fixes/roms-prsgrd40-wetdry.md) (a compile fix).
- SWAN:
  - [a NetCDF output crash](build/coawst/patches/1-fixes/swan-nc-crash.md);
  - [stop on input errors](build/coawst/patches/1-fixes/swan-stop-on-input-errors.md);
  - [output coordinates and missing points](build/coawst/patches/1-fixes/swan-output-fixes.md);
  - [`FORCE` at process boundaries](build/coawst/patches/1-fixes/swan-force-strip-rows.md);
  - [vegetation](build/coawst/patches/1-fixes/swan-vegetation-fixes.md);
  - [periodic grids](build/coawst/patches/1-fixes/swan-periodic-fixes.md);
  - [a halo-exchange deadlock](build/coawst/patches/1-fixes/swan-halo-hang.md);
  - [exact restarts](build/coawst/patches/1-fixes/swan-exact-restart.md).

**Improvements**:
- [SWAN NetCDF output of every quantity](build/coawst/patches/2-improvements/swan-netcdf-output.md);
- [compressed SWAN NetCDF-4](build/coawst/patches/2-improvements/swan-netcdf4-compression.md);
- [periodic curvilinear SWAN grids](build/coawst/patches/2-improvements/swan-periodic-curvilinear.md);
- [faster spectral Stokes drift](build/coawst/patches/2-improvements/roms-wec-stokes-fast.md);
- [closed O-grids round an island](build/coawst/patches/2-improvements/swan-closed-ring.md);
- [build settings](build/coawst/patches/2-improvements/build-settings.md):
  compiler flags, `SWAN_SINGLESPEC` off, compressed output.

**Experimental (off by default)**:

| Patch | Switch it on with | What it does | Status |
|---|---|---|---|
| [roms-step2d-fb](build/coawst/patches/3-experimental/roms-step2d-fb.md) | `STEP2D_FB_AB3_AM4` | ROMS's AB3-AM4 barotropic kernel, completed with COAWST's wave and vegetation terms | as accurate as the default LF-AM3 against a 4x-smaller-step reference; 2-D kernel 2.4-2.6x less CPU |
| [roms-veg-implicit](build/coawst/patches/3-experimental/roms-veg-implicit.md) | `VEG_DRAG_IMPLICIT` | canopy drag taken implicitly: no time-step limit for dense or patchy canopies | stable where explicit drag blows up; within 1 cm/s of explicit at a safe step |
| [roms-bstress-implicit](build/coawst/patches/3-experimental/roms-bstress-implicit.md) | `BSTRESS_IMPLICIT` | bottom stress taken implicitly instead of capped | the full stress where `LIMIT_BSTRESS` would bind (thin bottom layers under fast flow); matches the uncapped explicit stress to 1 % on thin-crest A15 variants |
| [wec-break-uniform](build/coawst/patches/3-experimental/wec-break-uniform.md) | `WEC_BREAK_UNIFORM` | breaking force spread evenly over depth | a sensitivity switch |

Switch one on with `-- --build-arg CPP_OPTIONS="+VEG_DRAG_IMPLICIT"`.

**Will my results change?** Each patch's status card answers this. In short:
- **Unchanged.** Crash, hang and output fixes, and the improvements, leave
  the computed solution unchanged, or change it at the level of rounding.
- **Changed, if you use the feature.** The vegetation, Stokes drift,
  `WET_DRY` + waves, sediment-tiling and SWAN vegetation fixes change results
  in cases that use those features.
- **Changed in the last digits.** The build settings (FMA instructions, no
  `-ffast-math`) change the last digits of every run compared with COAWST's
  own flags.

## ROMSPath (particle tracking)

[ROMSPath](https://github.com/imcslatte/ROMSPath) (Hunter et al., 2022) tracks
particles offline in ROMS output: 4th-order Runge-Kutta advection on the ROMS
grid, vertical and horizontal turbulence, behaviour, nested grids.

```bash
build/romspath/build.sh                      # image coawst-romspath:latest (~200 MB)
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/run" coawst-romspath ROMSPath.exe ROMSPath.data
```

It is built from the fork [NicJeffress/ROMSPath](https://github.com/NicJeffress/ROMSPath)
at a pinned commit. The fork is upstream plus:
- periodic boundaries;
- eight fixes, one commit each, to be offered upstream:
  - the wrap across the periodic seam;
  - particle placement on curvilinear grids;
  - the hydrodynamic record timing, which was one record behind;
  - the Runge-Kutta stages;
  - the turbulence spline weights;
  - slow per-particle timers.

On a periodic channel with an exact answer, the unfixed code is 48 m off after
2 h; the fixed code is exact. See [`build/romspath`](build/romspath/README.md).

ROMSPath has no license upstream, so this repository holds no ROMSPath code,
only the instructions to fetch and build it.

## Tests

Every patch has a test that builds COAWST before and after it, runs a case,
and prints PASS or FAIL. Its results are written up in the patch's document.
The [test index](tests/README.md) lists them all, with run times from 10
minutes to 1.5 hours on 4 cores.

| Kind | What | Where |
|---|---|---|
| Per patch | fix: fails without, passes with; improvement: results unchanged; experimental: build unchanged with the option off | `tests/fixes/`, `tests/improvements/`, `tests/experimental/` |
| COAWST's examples | 15 ROMS/SWAN examples, built as stock COAWST, with the patches, and with the engine's settings; outputs compared | [`tests/examples/`](tests/examples/README.md) |
| Test cases | an idealized fringing reef with a pass (periodic, curvilinear, with and without vegetation); a round island on a closed O-grid; a standalone periodic SWAN case | [`tests/cases/`](tests/README.md#test-cases) |
| ROMSPath | every fork commit on a periodic channel with an exact answer | [`tests/romspath/`](tests/romspath/periodic-channel/README.md) |
| The series itself | does a reorganised series give the same source; code or comments only | [`tests/same_source/`](tests/README.md#checks-on-the-patch-series) |

### Automated checks

GitHub Actions run the quick checks. The scripts behind them run the same way
on any machine with Docker.

| When | Check | Script |
|---|---|---|
| every push and pull request | the series is complete (every patch listed, each with its document) and applies to the pinned COAWST | `tests/ci/series_check.sh` |
| every push and pull request | ROMSPath: every fork commit and the image on the periodic channel | `tests/romspath/periodic-channel/run.sh` |
| pull requests, by hand, weekly | build COAWST with all patches; run Inlet_test coupled for an hour; no NaN; output is compressed NetCDF-4 | `tests/ci/inlet_smoke.sh` |
| weekly | the series on COAWST's latest `main`; the ROMSPath fork on upstream's latest master | `tests/ci/series_check.sh main`, `tests/ci/romspath_upstream.sh` |

The weekly checks do not test the engine itself, which builds pinned commits.
They warn early when an upstream update would need work, and say which patch
or commit is affected. The long tests (one per patch, the examples sweep)
run on a workstation or on Cloud Batch at each release.

## Reproducibility and provenance

- **Pinned sources.** COAWST and ROMSPath are built at fixed commits. Each
  image records what it was built from:
  - `/opt/coawst/COAWST_COMMIT` and `/opt/coawst/PATCHES_APPLIED` in the
    COAWST image;
  - `/opt/romspath/PROVENANCE` in the ROMSPath image.
- **Same answer on any machine.** There is no `-ffast-math`, and the CPU
  target is generic x86-64-v3, not the build machine's. The same image with
  the same MPI layout gives bit-identical results run after run, on Intel and
  AMD.
- **Exact restarts.** A run stopped and restarted from its restart files
  continues exactly as if it had not stopped. This is what makes interruptible
  (Spot) cloud machines usable for long runs.
- **Upstream changes tracked.** A weekly check tries our patches on COAWST's
  latest code and our ROMSPath commits on ROMSPath's.

## Repository layout

```
build/
  coawst/
    Dockerfile, build.sh, apply_series.sh   build the COAWST image (README.md: build and run guide)
    patches/
      series                                the order the patches are applied in
      1-fixes/, 2-improvements/,
      3-experimental/                       <name>.patch + <name>.md (its document)
      generators/                           writes the SWAN patches from SWAN's source
    vendor/                                 optional offline COAWST tarball
  romspath/                                 build the ROMSPath image from the fork
tests/
  fixes/, improvements/, experimental/      one test per patch (run.sh, check script, README)
  examples/                                 COAWST's examples, built three ways
  cases/                                    test cases (idealized reef, round island, periodic SWAN)
  romspath/                                 ROMSPath periodic-channel test
  ci/                                       scripts behind the automated checks
  same_source/                              checks on the patch series
  tools/                                    shared runners and comparison tools
docs/figures/                               figures used by the patch documents
docs/manuals/                               where to put the COAWST, SWAN and ROMS manuals (not included; README: versions, caveats)
docs/options/                               every ROMS/SWAN/coupling/build option with the choice for the
                                            idealized reef cases and its reasoning; SWAN command catalogue
.github/workflows/                          the automated checks
```

## Roadmap

- **Cloud Batch launcher** (`launch/`): run every member of an ensemble on
  Google Cloud Batch:
  - one task per member;
  - region and machine choice within quota;
  - Spot machines with exact restarts in segments;
  - inputs and outputs in a bucket;
  - a cost log.
- **Upstream:** report the fixes to COAWST, one pull request per fix; offer
  the ROMSPath fixes to its authors; ask them for a license.
- **Validation report** for each release: every test with its pass/fail and
  key number, and a figure per test.

## Licenses and citation

Our own code is under the MIT license ([`LICENSE`](LICENSE)). COAWST and the
models it contains keep their own licenses ([`THIRD_PARTY.md`](THIRD_PARTY.md)):
- COAWST's USGS parts are public domain;
- ROMS is MIT;
- SWAN is GPL, so our SWAN patches are GPL too;
- MCT and SCRIP use BSD-style licenses.

ROMSPath has no license file upstream; it is fetched from its fork at build
time and not copied here.

If you use this in published work, cite the models themselves:
- **COAWST:** Warner, Armstrong, He and Zambon (2010), *Ocean Modelling*.
- **ROMS:** Shchepetkin and McWilliams (2005), *Ocean Modelling*.
- **SWAN:** Booij, Ris and Holthuijsen (1999), *Journal of Geophysical Research*.
- **ROMSPath,** if used: Hunter et al. (2022), *Geoscientific Model Development*.

Please also mention the patch series, ideally with the commit of this
repository you used. COAWST asks users not to imply endorsement by the USGS.
