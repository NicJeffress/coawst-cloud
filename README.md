# coawst-cloud

Patched, containerized COAWST (ROMS + SWAN) and ROMSPath, with tools to run large
ensembles on Google Cloud.

> **Status: under construction.** The repository is being built up one change at a
> time: first COAWST as shipped, then each patch with its documentation and test.

## What is here

| Part | What it does |
|---|---|
| `build/coawst/` | Builds COAWST from the public repository at a pinned commit, applies a documented series of patches, and packs ROMS + SWAN (coupled through MCT) into a container image. The image runs anywhere Docker or Apptainer runs: a laptop, a university cluster, the cloud. |
| `build/romspath/` | (planned) The same for the ROMSPath particle-tracking model. |
| `launch/` | (planned) Runs many members of an ensemble on Google Cloud Batch: region choice, Spot machines with exact restarts, inputs and outputs in a bucket, cost log. |
| `tests/` | Checks behind each patch, and tools for checking the patch series itself. |

## Patches

Patches are grouped by how well established they are (`build/coawst/patches/series`):

- **fixes**: COAWST did something wrong. Each has a test that fails without the
  patch and passes with it.
- **improvements**: no change to the physics, or a new capability. Each has a test
  that results are unchanged.
- **experimental**: off unless a cpp option switches them on; with the option off
  the build is unchanged.

## Building

```bash
build/coawst/build.sh                                  # stock Inlet_test
build/coawst/build.sh -- --build-arg SERIES=none       # same, without our patches
build/coawst/build.sh --case path/to/MyCase --app MY_CASE
```

## Licenses

Our own code is under the MIT license (`LICENSE`). COAWST and the models it
contains keep their own licenses; see `THIRD_PARTY.md`. Patches to SWAN are
covered by SWAN's GPL.
