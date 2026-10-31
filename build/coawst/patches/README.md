# COAWST patches

`series` lists the patches in the order they are applied. They are grouped in
three folders by how well established they are:

| Folder | Kind | What its test must show |
|---|---|---|
| `1-fixes/` | COAWST did something wrong | fails without the patch, passes with it |
| `2-improvements/` | no change to the physics, or a new capability | results unchanged (bit-identical or rounding level) |
| `3-experimental/` | off unless a cpp option switches it on | build unchanged with the option off; what has and has not been checked |

Several patches edit the same files, so they only apply in this order. An
experimental patch moves to the improvements after an accuracy test against a
converged reference.

Each patch is documented here with a status card:

| Field | Meaning |
|---|---|
| Type | fix, improvement or experimental |
| Changes results? | no (crash, output or run-control fix only), output (values written change, the computation does not), yes (the computed solution changes, in the cases named), speed, new (a capability COAWST did not have) |
| Default | on, or the cpp option that switches it on |
| Evidence | the test case and the numbers |
| Test | the script that checks it |
| Upstream | reported or proposed to COAWST? |

## The patches

Each patch has a document of the same name next to it: what was wrong, why it
matters, the fix, how it was found, the test and its results, and its limits.

### 1. Fixes

| Patch | What was wrong | Changes results? | Test |
|---|---|---|---|
| [roms-sed-morph-tiling](1-fixes/roms-sed-morph-tiling.md) | With sediment morphology, results depended on the MPI tiling (three halo bugs) | yes, multi-tile `SED_MORPH` runs | 1x1 vs 1x2 tiles, Inlet_test |
| [roms-wec-stokes-fixes](1-fixes/roms-wec-stokes-fixes.md) | The u-point spectral Stokes drift loop was not the mirror of the v-point loop (wrong neighbour, bin limit, unused SINH) | yes, `SPECTRUM_STOKES` (up to 3.7 % of u_stokes in Inlet_test); faster | source check + Inlet_test |
| [roms-limit-bstress](1-fixes/roms-limit-bstress.md) | The bottom-stress limiter tested `WET_DRY` instead of `LIMIT_BSTRESS` | no for existing builds; enables `-WET_DRY +LIMIT_BSTRESS` | preprocessed Fortran, Veg_test |
| [swan-nc-crash](1-fixes/swan-nc-crash.md) | SWAN's NetCDF output read 140 bytes from an 11-byte file name, and indexed its name table past the end | no (memory safety; crash on some machines) | SWAN with -fcheck=bounds, Inlet_test |
| [swan-stop-on-input-errors](1-fixes/swan-stop-on-input-errors.md) | After SWAN rejected its input, the coupled run carried on with SWAN half set up | no (run control) | Inlet_test with a rejected request |
| [swan-output-fixes](1-fixes/swan-output-fixes.md) | NetCDF TABLE points at the grid origin (several SWAN processes), -1e10 grid coordinates (one process), output between grid points randomly missing | output only | Inlet_test with extra output, 1 and 2 SWAN |
| [swan-vegetation-fixes](1-fixes/swan-vegetation-fixes.md) | COAWST's vegetation routine in SWAN (VEGETATION 3) read an unallocated array, kept flexible plants rigid, used Cd 1.95 for emergent plants and wrote Cd as 0; SWAN's plant input read the wrong input grids | yes, VEGETATION 3 and SWAN's own plant input | source check + Veg_test with VEGETATION 3 |
| [swan-periodic-fixes](1-fixes/swan-periodic-fixes.md) | Periodic SWAN (REPEATING): COMPGRID output interpolated between grid points; several processes on x-strips crashed or gave garbage; spectral Stokes fields sent to ROMS shifted | yes, periodic SWAN | source check + standalone periodic reef, 1 and 4 processes |
| [swan-halo-hang](1-fixes/swan-halo-hang.md) | SWAN's halo exchange deadlocked once a row exceeded MPI's eager limit (blocking sends) | no (deadlock fix) | periodic channel, 1100-point rows, 2 processes |

The SWAN patches are written by [`generators/make_swan_patches.py`](generators/make_swan_patches.py)
from the unpatched SWAN source; the item numbers in their documents are its
items.

More fixes (SWAN, vegetation, wet/dry Stokes transport, restarts) follow.
