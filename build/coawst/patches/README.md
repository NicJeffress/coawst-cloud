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
| [roms-vegetation](1-fixes/roms-vegetation.md) | Vegetation: work array too small for the halo exchange (crash with periodic boundaries), division by zero when plants cover the bed, tau_veg in the wrong units, wrong depth average for the v drag | yes: crash fixed; canopy eddy viscosity about 10 % lower | source check + Reef_Ideal_A15_veg runs |
| [roms-wec-stokes-fixes](1-fixes/roms-wec-stokes-fixes.md) | The u-point spectral Stokes drift loop was not the mirror of the v-point loop (wrong neighbour, bin limit, unused SINH) | yes, `SPECTRUM_STOKES` (up to 3.7 % of u_stokes in Inlet_test); faster | source check + Inlet_test |
| [roms-limit-bstress](1-fixes/roms-limit-bstress.md) | The bottom-stress limiter tested `WET_DRY` instead of `LIMIT_BSTRESS` | no for existing builds; enables `-WET_DRY +LIMIT_BSTRESS` | preprocessed Fortran, Veg_test |
| [roms-wetdry-stokes](1-fixes/roms-wetdry-stokes.md) | With WET_DRY, the first barotropic sub-step of every baroclinic step dropped the Stokes transport towards -x and -y | yes: up to 0.24 m/s in the idealized reef (nothing dries there); builds without WET_DRY bit-identical | Reef_Ideal_A15 with vs without WET_DRY |
| [roms-restart-wec](1-fixes/roms-restart-wec.md) | Restarts with waves were not exact (wave pressure term and volume fluxes missing from the restart file; river fluxes, GLS fields and bed properties lost at land points; turbulence ghost points left empty) | restarts only: now exact (with swan-exact-restart) | Reef_Ideal_A15_veg, A15 with a river and bare A15, straight vs restarted |
| [roms-restart-step-count](1-fixes/roms-restart-step-count.md) | When the start time is far from DSTART (a calendar-dated initial file with DSTART 0), ROMS's step counter overflowed to a garbage value: perfect restarts started cold or lost their place, fresh runs could put output on the wrong steps; now a perfect restart stops with a message, other runs start at 1 with a warning | only when the step number does not fit; otherwise bit-identical | Reef_Ideal_A15 with DSTART 730119 days before its start, before vs after; normal A15 unchanged |
| [roms-vandera-no-sand](1-fixes/roms-vandera-no-sand.md) | Van der A bedload with no sand class (mud only): the loop over sand never ran, yet its unset local arrays were copied to `fd_wbl` and the wave-shape output fields (garbage, different per build and per tile) | output only, only without sand; model state and runs with sand bit-identical | Inlet_test DiffGrid with unset memory as NaN: NaN before, zero after; Inlet_test Coupled bit-identical |
| [roms-prsgrd40-wetdry](1-fixes/roms-prsgrd40-wetdry.md) | The `PJ_GRADP` pressure gradient (`prsgrd40.h`) did not compile with `WET_DRY`: the wet/dry masks were passed and used but never declared | no: a compile fix; other builds identical | Reef_Ideal_A15 with `PJ_GRADP`: compile error before, compiles and runs after; identical executables without `WET_DRY` |
| [roms-quicksave-uv](1-fixes/roms-quicksave-uv.md) | The quicksave file defined the 3-D velocity `u`, `v` but the standard NetCDF writer never wrote them (fill values); only the PIO writer did | output only | Reef_Ideal_A15 quicksave vs history, before/after |
| [swan-nc-crash](1-fixes/swan-nc-crash.md) | SWAN's NetCDF output read 140 bytes from an 11-byte file name, and indexed its name table past the end | no (memory safety; crash on some machines) | SWAN with -fcheck=bounds, Inlet_test |
| [swan-stop-on-input-errors](1-fixes/swan-stop-on-input-errors.md) | After SWAN rejected its input, the coupled run carried on with SWAN half set up | no (run control) | Inlet_test with a rejected request |
| [swan-output-fixes](1-fixes/swan-output-fixes.md) | NetCDF TABLE points at the grid origin (several SWAN processes), -1e10 grid coordinates (one process), output between grid points randomly missing | output only | Inlet_test with extra output, 1 and 2 SWAN |
| [swan-force-strip-rows](1-fixes/swan-force-strip-rows.md) | With several SWAN processes, BLOCK output of FORCE lost the grid row or column at every strip boundary (block points on grid lines were given to the process below, which lacks Hs one halo row further out) | output only: FORCE complete; everything else bit-identical | Inlet_test FORCE on 1, 2, 3 SWAN processes, before vs after |
| [swan-vegetation-fixes](1-fixes/swan-vegetation-fixes.md) | COAWST's vegetation routine in SWAN (VEGETATION 3) read an unallocated array, kept flexible plants rigid, used Cd 1.95 for emergent plants and wrote Cd as 0; SWAN's plant input read the wrong input grids | yes, VEGETATION 3 and SWAN's own plant input | source check + Veg_test with VEGETATION 3 |
| [swan-periodic-fixes](1-fixes/swan-periodic-fixes.md) | Periodic SWAN (REPEATING): COMPGRID output interpolated between grid points; several processes on x-strips crashed or gave garbage; spectral Stokes fields sent to ROMS shifted | yes, periodic SWAN | source check + standalone periodic reef, 1 and 4 processes |
| [swan-halo-hang](1-fixes/swan-halo-hang.md) | SWAN's halo exchange deadlocked once a row exceeded MPI's eager limit (blocking sends) | no (deadlock fix) | periodic channel, 1100-point rows, 2 processes |
| [swan-exact-restart](1-fixes/swan-exact-restart.md) | SWAN's periodic restart files were always text and held only the spectra, so restarted runs drifted | restarts only (now exact) | standalone SWAN, 40 min straight vs 20 + 20 restarted |
| [swan-triads-nonstationary](1-fixes/swan-triads-nonstationary.md) | SWAN skipped the triad source term in the first iteration of every time step when currents are present: coupled runs (one iteration per step by default) never computed `TRIAD` | yes: coupled and nonstationary-with-currents runs with `TRIAD` now have triads; everything else bit-identical | Reef_Ideal_A15_veg before/after, and with `TRIAD` removed |

The SWAN patches are written by [`generators/make_swan_patches.py`](generators/make_swan_patches.py)
from the unpatched SWAN source; each change in their documents is named as
its function there (`change_<name>`).

### 2. Improvements

| Patch | What it improves | Changes results? | Test |
|---|---|---|---|
| [swan-netcdf-output](2-improvements/swan-netcdf-output.md) | SWAN refused most quantities as NetCDF and stored most others as packed 16-bit integers (Hs in 0.76 mm steps); now every 2-D quantity, as 32-bit float | output only (NetCDF files); the run is bit-identical | Inlet_test, each quantity as .nc and .mat |
| [swan-netcdf4-compression](2-improvements/swan-netcdf4-compression.md) | SWAN ignored `OUT_NETCDF4`/`DEFLATE` and always wrote classic, uncompressed files; now compressed NetCDF-4, as ROMS | output only: same values, files 2-4x smaller (with the options) | Inlet_test, three builds, every variable compared |
| [swan-periodic-curvilinear](2-improvements/swan-periodic-curvilinear.md) | SWAN refused periodic (REPEATING) curvilinear grids; now supported (period from an extra coordinate column, seam geometry, output search); also corrects FORCE at the seam of regular periodic grids | new capability; other grids unchanged | standalone SWAN, 12 setups: curvilinear = regular, seam moved through the pass, 1 vs 4 processes |
| [roms-wec-stokes-fast](2-improvements/roms-wec-stokes-fast.md) | The spectral Stokes drift evaluated SINH/COSH (or EXP) twice per layer and bin; rewritten exactly to one per W level | speed: wave-effects kernel -32 % CPU; results at rounding level | Reef_Ideal_A15 with PROFILE, before vs after |
| [swan-closed-ring](2-improvements/swan-closed-ring.md) | SWAN refused periodic curvilinear grids that close on themselves (O-grids round an island: zero period), and COAWST's coupler laid out their rows one column off; now accepted, with the coupler mapping ROMS columns 0..Lm+1 to SWAN's ring, and SWAN's isolated-point test wrapping round the seam | new capability; other grids unchanged (A15 bit-identical) | Circle_Island (round island, 216 x 80 O-grid): coupler map exact, layouts identical, seam moved, waves from all sides |
| [build settings](2-improvements/build-settings.md) (Dockerfile) | COAWST compiles SWAN at -O1 and ROMS with -ffast-math, and Inlet_test's SWAN_SINGLESPEC breaks spectral output with several SWAN processes; now SWAN -O3, both -march=x86-64-v3 -g, no -ffast-math, SWAN_SINGLESPEC off, compressed NetCDF-4 output (`OUT_NETCDF4 DEFLATE`) | speed: coupled A15 1.7x faster; results within 6e-5 relative; SPECOUT correct | Inlet_test SPECOUT 1 vs 2 SWAN; A15 on AMD and Intel |

### 3. Experimental

Off unless their cpp option is defined: with the options off, every build
preprocesses to the same Fortran with and without them (apart from line
numbers passed to ROMS's timers, and a comment line;
`tests/experimental/options-off`).

| Patch | What it does (option) | Status | Test |
|---|---|---|---|
| [roms-step2d-fb](3-experimental/roms-step2d-fb.md) | ROMS's AB3-AM4 barotropic kernel (one call per fast step), unusable as shipped, completed with COAWST's wave and vegetation terms (`STEP2D_FB_AB3_AM4`) | as close as LF-AM3 to a reference with 4x smaller steps; 2-D kernel 2.4-2.6x less CPU | A15 and Circle_Island vs LF-AM3 and a small-step reference |
| [roms-veg-implicit](3-experimental/roms-veg-implicit.md) | canopy drag taken backward Euler, no time-step limit (`VEG_DRAG_IMPLICIT`) | patchy canopy: explicit blows up at DT 6 s, implicit runs and stays within 1 cm/s of explicit at DT 3 s | A15_veg patchy and uniform canopies |
| [roms-bstress-implicit](3-experimental/roms-bstress-implicit.md) | bottom stress taken backward Euler instead of capped (`BSTRESS_IMPLICIT`, `SSW_BBL`, not `SPLINES_VVISC`) | the full stress where `LIMIT_BSTRESS` would bind: matches the uncapped explicit stress to 1 % on thin-crest A15 variants, where the cap halves the friction | A15, Circle_Island, thin-crest A15 |
| [wec-break-uniform](3-experimental/wec-break-uniform.md) | breaking force spread evenly over depth: a sensitivity switch (`WEC_BREAK_UNIFORM`) | profile even (top/bottom 0.998 against 188); currents change by up to 14 cm/s at the surface | A15 breaking diagnostics |
