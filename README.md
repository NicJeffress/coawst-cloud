# coawst-cloud

Patched, containerized COAWST (ROMS + SWAN) and ROMSPath, every change
documented and tested, with tools to run large ensembles on Google Cloud.

> **Status: pre-release.** The COAWST patch series (fixes, improvements,
> experimental options) and the ROMSPath image are complete, each change with
> its document and test. The Cloud Batch launcher (`launch/`) is still to
> come.

## What is here

| Part | What it does |
|---|---|
| [`build/coawst/`](build/coawst/) | Builds COAWST from the public repository at a pinned commit, applies a [documented series of patches](build/coawst/patches/README.md), and packs ROMS + SWAN (coupled through MCT) into a container image. |
| [`build/romspath/`](build/romspath/README.md) | Builds the ROMSPath particle tracker into a small image of its own, from a [fork](https://github.com/NicJeffress/ROMSPath) that adds periodic boundaries and fixes, one commit each. |
| `launch/` | (planned) Runs many members of an ensemble on Google Cloud Batch: region choice, Spot machines with exact restarts, inputs and outputs in a bucket, cost log. |
| [`tests/`](tests/README.md) | One test per patch (before and after), COAWST's own examples built three ways, test cases, and checks on the series itself. |

The images run anywhere Docker or Apptainer runs: a laptop, a university
cluster, the cloud.

## The COAWST patches

25 patches, grouped by how well established they are
([`build/coawst/patches/series`](build/coawst/patches/series)):

| Tier | Patches | What it means | What its test shows |
|---|---|---|---|
| fixes | 16 | COAWST did something wrong: crashes, hangs, wrong output, results that depend on the tiling, inexact restarts, wrong physics in the vegetation and wave-current code | fails without the patch, passes with it |
| improvements | 5, plus build settings | no change to the physics, or a new capability: SWAN NetCDF output, periodic curvilinear and closed O-grid SWAN grids, faster Stokes drift | results unchanged |
| experimental | 4 | off unless a cpp option switches them on: an AB3-AM4 barotropic kernel, implicit vegetation drag and bottom stress, a breaking-force test switch | the build is unchanged with the option off |

Each patch has a document next to it (`<tier>/<name>.md`) with a status card.
The card says:
- whether it changes results;
- whether it is on by default;
- the evidence;
- its test;
- whether it has been reported upstream.

The document explains the bug and shows the code before and after; the
[patch index](build/coawst/patches/README.md) lists them all.

COAWST ships 15 examples that use only ROMS and/or SWAN. None of them fails on
stock COAWST v3.9, and every difference our patches make to them is traced to
a named patch ([examples sweep](tests/examples/README.md)).

## Building

```bash
build/coawst/build.sh                                  # Inlet_test, with all patches
build/coawst/build.sh --series none -- --build-arg BUILD_SETTINGS=stock
                                                       # COAWST exactly as shipped
build/coawst/build.sh --case path/to/MyCase --app MY_CASE
build/coawst/build.sh -- --build-arg CPP_OPTIONS="+VEG_DRAG_IMPLICIT"
build/romspath/build.sh                                # ROMSPath
```

A case folder holds its header (`mycase.h`), analytical files and `.in`
files; the build copies it into COAWST's `Projects/`. The cpp options are
compiled in, so an ensemble that varies only `.in` files and input NetCDF
shares one image.

## Automated checks

GitHub Actions run the quick checks. The scripts behind them run the same way
on any machine with Docker ([tests/README.md](tests/README.md#automated-checks)).

| When | Check | Script |
|---|---|---|
| every push and pull request | the series is complete and applies to the pinned COAWST | `tests/ci/series_check.sh` |
| every push and pull request | ROMSPath, every fork commit and the image, on a periodic channel with an exact answer | `tests/romspath/periodic-channel/run.sh` |
| pull requests, by hand, weekly | build COAWST with all patches and run Inlet_test (coupled) for an hour | `tests/ci/inlet_smoke.sh` |
| weekly | the series on COAWST's latest `main`; the ROMSPath fork on upstream's latest master | `tests/ci/series_check.sh main`, `tests/ci/romspath_upstream.sh` |

The long tests (one per patch, and the examples sweep) take from minutes to
hours. They run on a workstation, or on Cloud Batch at each release.

## Licenses

Our own code is under the MIT license ([`LICENSE`](LICENSE)). COAWST and the
models it contains keep their own licenses ([`THIRD_PARTY.md`](THIRD_PARTY.md)).
Patches to SWAN are covered by SWAN's GPL. ROMSPath has no license file
upstream yet, so this repository holds no ROMSPath code, only the instructions
to fetch and build it.
