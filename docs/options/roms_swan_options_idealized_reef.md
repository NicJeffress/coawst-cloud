# ROMS, SWAN, coupling and build options for the idealized reef cases

A catalogue of every physics and numerics option in the ROMS and SWAN of
COAWST v3.9 (and of the coupler and the compiler), with a recommendation
for each one for the idealized reef cases, and the reasoning behind it.
Written 2026-11-02 from the sources listed at the end. No new test runs
were made for it: where the recommendation rests on a run, that run was
done earlier and is cited; where it rests on theory, the argument is
given and the option is marked **to test**.

The cases (`Reef_Ideal_A15` and its `_veg`, `_veg_strat`, `_veg_therm`
variants, `tests/cases/`): one fringing reef with a pass, 203 x 111
points, 10 levels, 20-80 m cells, east-west periodic, crest 0.5 m deep,
forereef down to 400 m; waves Hs 1 m / Tp 10 s from the north, 0.15 m
tide, coral canopy, optionally stratification and diurnal heating; no
Coriolis (f = 0 in the grid file), no wind. Where a realistic reef case
run with the same engine taught something about an option, it is quoted
as "the realistic case" (its records are private).

## How to read this document

- Option names are the cpp names of `ROMS/Include/cppdefs.h` and
  `globaldefs.h` and the keywords of `ocean.in`, `vegetation.in`,
  `coupling.in` and `swan.in` at the pinned COAWST commit
  `26e6fb7` (2 October 2026). Where the source and a manual disagree,
  the source wins and the disagreement is noted. The COAWST manual
  (September 2026) and the SWAN manuals (41.51, March 2026) are current,
  but the COAWST manual's ROMS section describes an older ROMS, and
  "Living with ROMS" (2020) predates COAWST v3.9: both are used for
  reasoning, not for option names.
- **Status words.** *Use*: recommended now. *Keep off*: not for these
  cases. *To test*: theory says it should help, no run yet. *Sensitivity*:
  a switch for checking how much a result depends on an assumption.
  *Not for us*: a different kind of application (data assimilation,
  biology, sea ice, WRF).
- Evidence is quoted from the project's run records (a dated lab
  notebook and case READMEs, private) and from the patch documents of this
  repository (`build/coawst/patches/*/*.md`). Each quoted number names its
  source.

## Summary: the recommended configuration

The table gives the choice for the idealized reef (A15 and its
variants). Details and reasoning follow in the numbered sections.

| Topic | Choice | Section |
|---|---|---|
| Grid | rectilinear, stretched, `CURVGRID` off (dndx = dmde = 0); on for curvilinear grids | 1.1 |
| Wetting and drying | off (nothing dries); `LIMIT_BSTRESS` or `BSTRESS_IMPLICIT` carries the stress limiter that `WET_DRY` used to bring when a case needs one | 1.1, 1.5 |
| Momentum advection | default U3H/C4V (`UV_ADV` only) | 1.2 |
| Horizontal viscosity | `UV_VIS2` compiled with `VISC2` 0 (the U3 scheme's own hyperdiffusion is the lateral viscosity), `MIX_S_UV`; sponge via `visc_factor` only at an open boundary | 1.2 |
| Pressure gradient | `DJ_GRADPS` | 1.3 |
| Equation of state | linear (`TCOEF` 3.2e-4 at 28 C) for single-stratification runs; `NONLIN_EOS` once river water and realistic T/S are used (**to test**: rest run first) | 1.4 |
| Tracer advection | MPDATA for T, S and dyes | 1.4 |
| Vertical mixing | GLS k-epsilon, `KANTHA_CLAYSON`, `RI_SPLINES`, `N2S2_HORAVG` (off with `VEG_TURB`) | 1.6 |
| Surface turbulence from breaking | `TKE_WAVEDISS` + `ZOS_HSIG` **to test** (currently neither: breaking injects no TKE) | 1.6 |
| Bottom stress | `SSW_BBL` + `SSW_CALC_ZNOT` + `SSW_LOGINT_WBL`; explicit and uncapped as now (converged in DT on A15); `LIMIT_BSTRESS` only if stronger forcing destabilizes it; `BSTRESS_IMPLICIT -SPLINES_VVISC` when the crest jet is the target (and on shallower, faster crests) | 1.5 |
| Roughness | `grain_diameter` in the initial file (0.12 m = z0 0.01 m) and/or canopy drag: usually one or the other, but both is allowed (a rough bed under a canopy; the A15 canopy cases have both); SWAN gets KN = 30 z0 from ROMS | 1.5, 5 |
| Canopy | `VEGETATION` + `VEG_DRAG` + `VEG_TURB` (+ `VEG_SWAN_COUPLING`, SWAN `VEGETATION 3`); explicit drag, `VEG_DRAG_IMPLICIT` for patchy or dense canopies; `VEG_FLEX` off | 1.7 |
| Wave forcing | `WEC_VF`, `WDISS_WAVEMOD`, `SPECTRUM_STOKES`, `UV_KIRBY`; **Reniers roller (`WEC_ALPHA` 0.5), `BOTTOM_STREAMING` and `VEG_STREAMING` on since 2026-11-03**; `DISSIP_BREAK_DIR` never with SWAN | 1.8 |
| Surface fluxes | analytic heat flux with SST feedback now; `BULK_FLUXES` + `SOLAR_SOURCE` + `WIND_MINUS_CURRENT` when winds arrive | 1.9 |
| Open boundary | periodic E-W; north: `Che`/`Shc`/`RadNud` + interior nudging band, TKE `Gra`, Stokes `Gra` | 1.10 |
| Barotropic kernel | LF-AM3 (default) or `STEP2D_FB_AB3_AM4` (as accurate, 2.4x cheaper 2-D kernel; the realistic case's default) | 2.3 |
| Time step | **A15: DT 3 s, NDTFAST 12 since 2026-11-04** (the author: stay below the CFL limits; with streaming at N 15, DT 6 s had vertical Courant above 1 on 90-96 % of steps on density 1, and the bare reef blows up at DT 6 and 4 s); before: DT 6 s, NDTFAST 24; barotropic Courant 0.8-0.85; shallower and faster crests need 4 s or 2 s | 2.2 |
| Vertical grid | N 15 (since 2026-11-03; was 10), Vtransform 2, Vstretching 4, theta_s 3, theta_b 2, Tcline 20 | 2.1 |
| SWAN physics | `GEN3` (no wind: inert), **`BREAKING BKD 1.0 0.54 7.59 -8.06 8.09` (A15 default since 2026-11-03, author; was CON 1.0 0.73)**, `FRICTION MADSEN` (KN from ROMS), `TRIAD` (DCTA), `OFF QUAD`; `VEGETATION 3` with the canopy | 3 |
| SWAN numerics | nonstationary, `PROP BSBT`, dt 120 s, one iteration per step, default limiter; `CTHETA` tested 2026-11-03: not needed (within 0.7 %) | 4 |
| Coupling | MCT, same grid, 600 s exchange; 300 s **sensitivity** | 5 |
| Build | gfortran `-O3 -march=x86-64-v3 -g`, no `-ffast-math`; SWAN `-O3`; `OUT_NETCDF4 +DEFLATE`; MPI only | 6 |

## Contents

1. ROMS physics options (cpp)
2. ROMS numerics (cpp and `ocean.in`)
3. SWAN physics (`swan.in`)
4. SWAN numerics (`swan.in`)
5. Coupling (`coupling.in`, coupler cpp options)
6. Compiler and build options
7. The recommended configurations in full, and what to test first
8. Sources

## 1. ROMS physics options (cpp)

The cpp options are compiled into the executable (the case header
`<app>.h`, plus `CPP_OPTIONS="+X -Y"` at build time). Each subsection
lists the family of options, says what each does, and ends with the
recommendation. Internal options that `globaldefs.h` switches on by itself
(`WEC`, `BBL_MODEL`, `SPECTRUM_STOKES`, `WAVES_*`, `MASKING` with
`WET_DRY`, `LIMIT_BSTRESS` with `WET_DRY`) are mentioned where they
matter and must not be put in the header.

### 1.1 Model configuration

| Option | What it does | Choice |
|---|---|---|
| `SOLVE3D` | 3-D primitive equations with the split barotropic mode. Off = 2-D shallow water. | on |
| `CURVGRID` | curvilinear metric terms (`dndx`, `dmde`) and the grid angle in the momentum equations. ROMS always uses `pm`, `pn` from the grid; `CURVGRID` only adds the curvature terms. | off: A15's grid is rectilinear and stretched, `dndx = dmde = 0` and `angle = 0` in the grid file, so the terms vanish; on for any curvilinear grid |
| `MASKING` | land/sea masks. | on |
| `SPHERICAL` | analytical spherical grid; not for grids read from files. | off |
| `WET_DRY` (+ `DCRIT` in `ocean.in`) | cells shallower than `DCRIT` dry out: momentum faces into them are blocked and the masks become time dependent. Also implies `MASKING` and, in COAWST, `LIMIT_BSTRESS` (`globaldefs.h` lines 152-163). | off |
| `LIMIT_BSTRESS` | caps the bottom stress so it cannot reverse the bottom-layer flow in one step (section 1.5). In stock COAWST it is only reachable through `WET_DRY`; the engine's `roms-limit-bstress` fix makes it an independent switch. | off as built (A15 runs the explicit stress uncapped and stays stable at DT 6 s); turn on only if a stronger forcing destabilizes a member; the realistic case keeps it on, or replaces it by `BSTRESS_IMPLICIT` |
| `UV_COR` | Coriolis term. | on, but the A15 grid has f = 0: no rotation. Turning rotation on (f = -4.4e-5 s-1 at 17.5 S) is a physics decision for the encyclopedia, not a numerics one; on a realistic reef it changed depth-averaged currents by about 1 cm/s RMS and up to 0.24 m/s where pass jets are deflected |
| `BODYFORCE` | applies surface and bottom stresses as body forces over `LEVSFRC`/`LEVBFRC` layers instead of as boundary fluxes. | off |
| `SINGLE_PRECISION` | single-precision kernel. | off |
| `PROFILE` | timing of every routine in the log. | on for benchmarks, otherwise off |
| `INLINE_2DIO` | process 3-D I/O level by level to save memory. | off |
| `NESTING` and its sub-options | grid refinement and composite grids. | off |

**Wetting and drying.** Keep it off as long as the shallowest water stays
above `DCRIT` through the lowest tide (A15: crest 0.50 m against a 0.15 m
tide; the realistic case: shallowest water 0.20-0.30 m, tide 0.10 m,
`DCRIT` 0.10 m). Reasons: with `WET_DRY` COAWST doubles the no-slip wall stress at
land (`pmask*pmask_wet`), and the wet/dry masking adds work in every
kernel (the realistic case ran 9 % faster without it, 2026-10-23). The
engine's
`roms-wetdry-stokes` fix removes the large error the stock code made with
`WET_DRY` and waves (Stokes transport dropped towards -i/-j, up to 0.24 m/s
in Inlet_test, 0.5 m/s near the realistic case's sand cays), so `WET_DRY` is safe to use
again when a case needs it: bigger tides, a shallower crest, or islets and
sand cays that flood and drain. Then also keep `DCRIT` at 0.10 m (ROMS's
masking logic assumes a few centimetres at least) and expect `PJ_GRADP` to
need the `roms-prsgrd40-wetdry` compile fix.

### 1.2 Momentum equations

**Advection.** The default (no flag besides `UV_ADV`) is 3rd-order
upstream-biased horizontal advection (U3H) and 4th-order centred vertical
advection (C4V) for the 3-D momentum, and 4th-order centred for the 2-D
momentum.

| Option | Scheme | Verdict |
|---|---|---|
| default (`UV_ADV` alone) | U3H + C4V. The upstream bias gives a built-in hyperdiffusion that removes grid-scale noise, so the explicit viscosity can stay tiny. | **use**. Both families run on it; no instability traced to it |
| `UV_C2ADVECTION` | 2nd-order centred: dispersive, needs real viscosity to stay clean. | keep off |
| `UV_C4ADVECTION` | 4th-order centred, no built-in damping; meant for eddy-resolving runs with `UV_VIS4`. | keep off |
| `UV_U3ADV_SPLIT` | U3 split into C4 advection plus a velocity-dependent biharmonic viscosity rotated along geopotentials (Marchesiello et al. 2009), to stop the upstream scheme from mixing across isopycnals on steep sigma layers. Forces `UV_C4ADVECTION`, `UV_VIS4`, `VISC_3DCOEF` and removes `UV_VIS2`. | keep off: on the realistic case it blew up near the crest within minutes, with or without `MIX_GEO_UV` (2026-10-23). The spurious mixing it cures is a deep-slope problem; our dynamics are on the reef flat |
| `UV_SADVECTION` | parabolic-spline vertical advection. The source warns: only idealized, high vertical resolution. | keep off (10 levels) |
| `OMEGA_IMPLICIT` | adaptive implicit vertical advection: relaxes the vertical Courant limit where it binds. | keep off: on A15 at N^2 = 1e-3 it hid the instability and produced a wrong solution (5 m/s, 15 C errors at the boundary) instead of crashing (`case_design.md`, constant stratification), and on the realistic case it held the vertical Courant number to 10-20 without stopping the runaway. Why, from the code: the paragraph after the viscosity tables below |

**Horizontal viscosity.**

| Option | What it does | Verdict |
|---|---|---|
| `UV_VIS2` + `VISC2` | harmonic (Laplacian) viscosity, coefficient `VISC2` in m2/s. | compiled in, **`VISC2` 0** in the A15 cases (user, 2026-11-02; 0.001 before): the U3 scheme supplies the lateral viscosity (see the paragraph on UCLA ROMS below), and `UV_VIS2` stays defined so that a `visc_factor` sponge can still be switched on |
| `VISC_GRID` | scales `VISC2` with cell size: `visc2_r = VISC2 * sqrt(dx dy) / max(sqrt(dx dy))` (`ini_hmixcoef.F` line 308; cubic scaling for `VISC4`), so the `.in` value applies at the largest cell. | **use**: the grid is stretched (20-80 m) |
| `MIX_S_UV` / `MIX_GEO_UV` | mixing along sigma layers or along geopotentials. Geopotential rotation adds a time-step restriction (Arango, Living with ROMS section 9) and only matters where sigma layers are steep and the viscosity large. | `MIX_S_UV`: with `VISC2` this small, the operator is a 2dx filter, not physics |
| `UV_VIS4` + `VISC4` | biharmonic. Only with centred advection. | keep off |
| `UV_SMAGORINSKY` | viscosity from the resolved strain rate (Smagorinsky), scaled by cell area. Adapts itself to jets and to varying resolution. | **sensitivity** for grids whose cell size varies a lot (the realistic case spans 10-470 m), where the crest jets are where grid-scale noise appears. Ilicak et al. (2012, quoted in Living with ROMS section 19) found Smagorinsky viscosity reduces spurious mixing in centred-scheme models; with U3 the gain is smaller. Not needed on A15 |
| `LuvSponge`, `LtracerSponge` (`ocean.in`) with `visc_factor`, `diff_factor` from the grid file (or `ANA_SPONGE`) | multiplies the coefficients in a band (A15's grid file: x1 to x5000 in the outer rows). | off by default (decided 2026-10-23): a +10 m2/s viscous sponge failed earlier than no sponge in the A15 stratified blow-up test, and the nudging band does the job. Note from Living with ROMS section 5.1: noise can appear where `visc_factor` changes even if `VISC2` is 0 |
| `VEG_HMIXING` + `VEGHMIXCOEF` (`vegetation.in`, 0.1) | extra horizontal viscosity at the edges of canopy patches (`VISC_3DCOEF`). | **to test** with patchy canopies: the explicit-drag blow-ups started where fast flow from bare gaps enters dense patches, which is exactly where this term acts. Untested; no reference run exists |

**Why so little explicit viscosity is right.** With U3 advection the
scheme's own damping scales with |u| dx^3, so it is already stronger where
flow is fast. Rule of thumb from the ROMS forum (Living with ROMS section
19): choose `visc2` so that the 2dx damping time scale (dx/pi)^2/visc2 is
a fraction of a day. For dx = 20 m that gives visc2 of order 1e-3 m2/s or
less; on a 10 m reef-crest grid even less. The grid Reynolds number
U dx / visc2 is 1e4 on A15 (U 0.5 m/s) and would need visc2 of 1 m2/s to
reach the "below 10" that Ilicak et al. recommend for centred schemes;
that recommendation does not apply to upstream-biased advection, and
1 m2/s would smear the crest jets. Keep 0.001 and let U3 work.

**Scheme-provided viscosity, explicit viscosity, and what UCLA ROMS does.**
The 3rd-order upstream-biased scheme is a 4th-order centred flux plus an
upwind correction proportional to |U| times the third difference of the
velocity (`gamma` term in `rhs3d.F`; UCLA's `compute_horiz_rhs_uv_terms.h`
has the same lines). Its leading truncation term is a hyperviscosity of
about |U| dx^3 / 12 acting on the fourth derivative: flow dependent,
selective to the 2dx scale, and zero where the flow is at rest. On the A15
crest (U 0.5 m/s, dx 20 m) that is 330 m4/s, a 2dx damping time of about
5 s; in a lagoon corner at 2 cm/s still about 2 min. The explicit
Laplacian `VISC2` 0.001 m2/s damps 2dx in about 11 h at 20 m cells, four
orders of magnitude weaker, and only overtakes the scheme's damping where
\|U\| drops below about 1e-4 m/s. So the former setting of 0.001 was "let the scheme
do it" in all but name, and since 2026-11-02 the A15 cases set `VISC2` to 0
outright. UCLA ROMS makes this explicit: `UPSTREAM_UV`
(momentum, `step3d_uv1.F`), `UPSTREAM_TS` (tracers, `step3d_t_ISO.F`),
`SPLINE_UV` and `SPLINE_TS` (vertical) are hard-wired, `UV_VIS2` and
`TS_DIF2` are compiled, and every example input (`Examples/*/*.in`, from
the tidal and river cases to the wave-forced surf-zone case) sets
`VISC2 = 0`, `VISC4 = 0`, `TNU2 = 0` and `v_sponge = 1` m2/s: the
only explicit viscosity and diffusivity is the sponge ramp that
`set_nudgcof.F` adds over the 15 points next to an open boundary. For
these reef cases the two settings are interchangeable: every A15 result up
to 2026-11-02 was run with 0.001 and `VISC_GRID`; 0 is the UCLA
convention and changes nothing visible, and a `visc_factor` sponge can
still be switched on with `LuvSponge` because `UV_VIS2` stays compiled.
What would not be interchangeable is a `VISC2` large enough to matter
(1 m2/s to reach a grid Reynolds number of 10): it would smear the crest
jets. Where the recommendations and UCLA's defaults differ elsewhere:
tracers (UCLA's upstream-biased scheme is cheaper but not monotone, and
mixed more or overshot in the comparison of section 1.4, so MPDATA stays),
vertical momentum advection (UCLA splines, ROMS C4V here; `UV_SADVECTION`
is ROMS's spline option and is marked "idealized, high resolution only"),
and the isoneutral rotation `ADV_ISONEUTRAL` UCLA offers for deep
stratified runs (Rutgers' `UV_U3ADV_SPLIT` plays that role and blew up
here).

**Why `OMEGA_IMPLICIT` did not help, from the code.** The option
(`omega.F`, Shchepetkin's adaptive scheme) splits the sigma-coordinate
vertical velocity at every interface into an explicit part and an
implicit remainder `Wi`. The budget for the explicit part is a total
Courant number of `amax` = 0.75: `cw_max = 0.75 dz - (horizontal inflow
Courant number)`, where the horizontal part is the sum of the inflow
fluxes into the cell times dt pm pn (`omega.F` lines 211-215, 259-264,
355-370). Whatever vertical displacement exceeds that budget goes into
`Wi`, which the tracer and momentum correctors apply as a first-order
upwind implicit term inside the tridiagonal solve (`step3d_t.F` lines
1619-1660, `step3d_uv.F` lines 522-560; MPDATA receives `Wi` as an extra
flux in `mpdata_adiff.F`). Three consequences:

1. It only ever removes the vertical-advection stability limit. The
   horizontal advection stays explicit (U3 with the LF-AM3 predictor and
   corrector), with its own limit near a Courant number of 1 in one
   direction and less in two. Every runaway on record had the cross-shore
   Courant number at 0.7-1.0 or above (the realistic case's crest jet;
   the A15 pass jet under a 2 m sea switched on at t = 0, notebook
   2026-11-02), so the vertical Courant numbers of 5-186 were the symptom
   of a horizontal runaway, not its cause. Once the horizontal inflow
   alone exceeds 0.75, `cw_max` is negative and the whole vertical
   advection becomes implicit upwind, which damps the vertical structure
   but leaves the horizontal growth untouched.
2. It cannot help an internal-wave limit at all. The A15 failures at N^2
   >= 3e-4 start at the deep boundary columns where c1 dt / dx (c1 = N H /
   pi, about 4 m/s at 1e-3) exceeds 0.5-1: a horizontal, pressure-gradient
   driven instability of the baroclinic step. The implicit upwind vertical
   term absorbs the vertical motion the instability produces, so the run
   survives with an overturned, wrong stratification instead of stopping.
3. The split is not applied everywhere. The predictor step
   (`pre_step3d.F`) and the turbulence equations (`gls_corstep.F`) advect
   with `OCEAN%W`, which after the split holds only the explicit part:
   wherever the option is active the predictor and the TKE and length-scale
   fields miss the implicit share of the vertical transport, exactly on the
   crest where it matters, and the implicit share itself is first-order
   upwind. That is an accuracy loss where the scheme is active, with no
   gain where it is not.

Where it would help: thin layers with a large but physical vertical
Courant number and a small horizontal one, for example strong vertical
motion over a steep slope resolved by many levels. That is not our regime.
The diagnostic that settles it on A15 is in the campaign brief (phase 2):
the pass-jet runaway with `OMEGA_IMPLICIT` on, watching the horizontal
Courant number at the failing point.

### 1.3 Pressure gradient

In sigma coordinates the horizontal pressure gradient is the small
difference of two large terms; over steep slopes with stratification the
truncation error acts as a spurious force at rest. The error grows with
the slope parameters rx0 (Beckmann and Haidvogel) and rx1 (Haney; it
scales with rx0 and with the number of levels), with the curvature of the
density profile, and with compressibility if the equation of state has it
(Shchepetkin 2003; Living with ROMS section 14).

| Option | Scheme (`prsgrd.F` selects the file) | Verdict |
|---|---|---|
| none | standard density Jacobian (`prsgrd31.h`, Song 1998) | keep off: largest errors |
| `WJ_GRADP` | weighted density Jacobian (`prsgrd31.h`, Song 1998) | keep off: legacy |
| `DJ_GRADPS` | density Jacobian with cubic polynomial reconstruction of rho and z, monotonized by harmonic averaging of the elementary differences (`prsgrd32.h`, Shchepetkin and McWilliams 2003); the same scheme UCLA ROMS hard-wires | **use** |
| `PJ_GRADP` | finite-volume pressure Jacobian (`prsgrd40.h`, Lin 1997). Does not compile with `WET_DRY` in stock v3.9; the engine's `roms-prsgrd40-wetdry` fix adds the masks | keep off |
| `PJ_GRADPQ2`, `PJ_GRADPQ4` | pressure Jacobian with conservative quartic reconstruction (`prsgrd42.h`, `prsgrd44.h`); Q4 adds a WENO-style reconciliation step. The most accurate in Shchepetkin and McWilliams' seamount tests | keep off here |
| `ATM_PRESS`, `PRESS_COMPENSATE` | inverse-barometer forcing from `Pair`. | off until air pressure is forced |

**Evidence** (the realistic case at rest, N^2 = 1e-4, 12 h, rx1 2.8;
notebook 2026-10-23): worst
spurious current `DJ_GRADPS` 24 mm/s, `PJ_GRADPQ4` 175 mm/s, `PJ_GRADP`
740 mm/s and wrong from the first step. A 30 m mixed layer on top of the
same stratification made the `DJ_GRADPS` error several times larger (87
mm/s): sharp bends in the density profile are what hurts most at 10
levels. On A15 (gentle slopes, rx0 at most about 0.15) the error stays
below 4 mm/s over 24 h.

**Why the "best" scheme lost.** The quartic schemes assume the density
profile is smooth enough for a quartic fit across four levels; with 10
uneven levels over an rx1 2.8 slope the fit sees a kink at every
layer-thickness jump, and its monotonicity limiter then throws away the
accuracy. `DJ_GRADPS` degrades more gracefully. The better levers are
not numerical: smoother bathymetry where the stratified water is (rx0 <=
0.2 was the crest-smoothing rule that made the realistic case run; Shchepetkin's forum rule
is rx1 up to 3 safe, 5-6 usual, 8-10 "insane"), a flat bed over the last
rows before an open boundary (the A15 zero-gradient error came from a
sloping last row), no stratification where the water is really mixed
(lagoon), and a rest test (no forcing: every current is error) for every new grid
or stratification before a production run. The rest test is cheap and
settles the question for that grid; the scheme choice should not be
revisited without one.

### 1.4 Tracers and the equation of state

| Option | What it does | Verdict |
|---|---|---|
| `TS_FIXED` | tracers do not evolve (diagnostic density). | A15 base case: on; stratified and thermal cases: off |
| `SALINITY` | salinity as an active tracer. | on (needed with rivers; harmless elsewhere) |
| `NONLIN_EOS` | Jackett and McDougall (1995) nonlinear equation of state, with compressibility (in-situ density). Off = linear, `rho = R0 - R0 TCOEF (T - T0) + R0 SCOEF (S - S0)`. | A15 single-stratification runs: linear with `TCOEF` 3.2e-4 /C (TEOS-10 at 28 C, S 35; A15's old 1.7e-4 would weaken heating-driven flows by about 45 %, `case_design.md`). **To test for the thermal and river cases**: the thermal expansion coefficient of seawater changes from 2.6e-4 at 20 C to 3.8e-4 at 36 C, so with an 8-10 C daily range on the reef flat the linear law misstates buoyancy by up to 20 %, and river water (S 0-35) adds the T-S cross term. The price is the pressure-gradient error: compressibility makes in-situ density grow 4.5 kg/m3 per 1000 m, which the sigma-coordinate scheme sees as extra stratification (equivalent N^2 about 4e-5 s-2 at depth), and Rutgers ROMS has no `SPLIT_EOS` to remove it. on a domain with deep water, so: turn it on, repeat the rest test, compare with the linear run |
| `T_PASSIVE` (+ `NPT`, `ANA_PASSIVE`, `ANA_SPFLUX`, `ANA_BPFLUX`) | inert dye tracers `dye_01`.... | **use** for residence time and connectivity studies alongside the particles: cheap (one more MPDATA tracer each), Eulerian, no sampling noise. Initialize patches smoothly over several cells (Wilkin, Living with ROMS section 21) |
| `AGE_MEAN` | mean age of a passive tracer (two tracers per dye). | **to test** for lagoon residence time: it gives the age field directly |
| `TS_DIF2` + `TNU2`, `TS_DIF4` + `TNU4`, `TS_SMAGORINSKY`, `DIFF_GRID` | explicit horizontal diffusion of tracers (harmonic, biharmonic, flow dependent; grid scaled). | `TNU2 = 0`; `TS_DIF2` compiled in only where a `diff_factor` band is wanted. MPDATA and HSIMT need no explicit diffusion; Griffies' warning (Living with ROMS section 19.3): never biharmonic on tracers |
| `MIX_S_TS`, `MIX_GEO_TS`, `MIX_ISO_TS` (+ `TS_MIX_MAX_SLOPE`, `TS_MIX_MIN_STRAT`, `TS_MIX_STABILITY`, `TS_MIX_CLIMA`) | direction of the explicit tracer diffusion: along sigma (spurious diapycnal mixing on slopes), along z, or along isopycnals (with slope limits). | `MIX_GEO_TS` where `TS_DIF2` is on; irrelevant with `TNU2 = 0` |
| `Hadvection`, `Vadvection` (`ocean.in`, per tracer) | `U3`/`C4` (ROMS classic, cheap, over/undershoots), `C2`, `A4` (Akima), `SU3` (split U3; needs `TS_U3ADV_SPLIT`, `TS_DIF4` and a rotated mixing option), `HSIMT` (3rd-order TVD, Wu and Zhu 2010, monotone), `MPDATA` (recursive flux correction, positive definite, sharpest fronts), `SPLINES` (vertical only). | **`MPDATA` for every tracer**. Evidence (the realistic case, 13 h forced, 2026-10-23): MPDATA is monotone and mixes least; U3 + splines gives the same temperatures for less cost but overshoots by up to 0.16 C; HSIMT mixed 3x more. Shchepetkin's caveat (Living with ROMS section 11): MPDATA is sign preserving, not TVD; it can create a new extremum near a sharp front, which is one more reason to avoid grid-scale fronts in initial conditions. Cost: several passes and three ghost points |
| `TS_MPDATA_LIMIT` | limits the upwind corrector fluxes for stability. | keep off unless MPDATA itself misbehaves |
| `SPLINES_VDIFF` | parabolic-spline reconstruction of the vertical tracer flux in the implicit vertical diffusion. | **inert with MPDATA tracer advection** (tested 2026-11-03: bit-identical on the stratified case): `step3d_t.F` uses the spline only for tracers not advected with MPDATA; matters only with U3 or HSIMT tracers |
| `SOLAR_SOURCE` (+ `WTYPE`, `WTYPE_GRID`) | shortwave absorbed over depth with the Paulson and Simpson Jerlov profile (`WTYPE` 1 = clearest). Light reaching the bed heats the bottom cell. | **use** in every heated case (on in `_therm`). Jerlov type 1 is right for clear reef water; a `WTYPE_GRID` with a turbid lagoon class is a later refinement |
| `LIMIT_STFLX_COOLING` | no cooling below the freezing point. | off |
| `QCORRECTION`, `SCORRECTION`, `SRELAXATION` | SST/SSS restoring corrections to the fluxes. | off (no observed SST to restore to; the far-field nudging band does the equivalent at the boundary) |
| `TS_FIXED` with `BULK_FLUXES` | not allowed together. | - |

### 1.5 Bottom stress, bottom boundary layer and roughness

ROMS offers five bottom-stress formulations; the three BBL models need
waves.

| Option | Formulation | Verdict |
|---|---|---|
| `UV_LDRAG` (`RDRG`) | linear drag. | off |
| `UV_QDRAG` (`RDRG2`) | quadratic drag with a constant coefficient, on the bottom-cell velocity. | off: the coefficient would have to change with layer thickness (3 cm on the crest, 40 m offshore) |
| `UV_LOGDRAG` (`Zob`) | quadratic drag with the coefficient from the log law at the bottom cell's height. | the right current-only choice, but it ignores the waves |
| `UV_WAVEDRAG` | extra linear wave drag. | off |
| `MB_BBL` (Meinte Blaas), `SG_BBL` (Styles and Glenn 2000), `SSW_BBL` (Sherwood, Signell, Warner; Warner et al. 2008) | wave-current boundary-layer models: the wave orbital velocity and period from SWAN (`UBOT`, `TMBOT`) raise the current's bottom stress and give the maximum wave-current stress for sediment. SSW is the COAWST default and the one maintained with the vegetation and van der A code | **`SSW_BBL`** |

SSW sub-options (`ssw_bbl.h`):

| Option | What it does | Verdict |
|---|---|---|
| `SSW_CALC_ZNOT` | roughness from the bed: `zoN = 2.5 d50 / 30` (clamped to at least 5e-5 m and at most 0.9 of the reference height), plus optional ripple, bedload and biological terms. Without it, `zo = ZoBot(i,j)`, which is `Zob` from `ocean.in` or the grid file's `ZoBot` with `UV_DRAG_GRID` | **on as built**: A15's initial file carries `grain_diameter` 0.12 m everywhere, which is exactly z0 = 0.01 m = `Zob`. So the "roughness via `Zob`" route is really "roughness via `grain_diameter`": a spatially varying roughness is written into the initial file as d50 = 12 z0, and `Zob` in `ocean.in` is then unused. Alternative with the same result: `#undef SSW_CALC_ZNOT` and a `ZoBot` field in the grid file with `UV_DRAG_GRID` |
| `SSW_ZOBL`, `SSW_ZORIP`, `SSW_ZOBIO` | add bedload-saltation, ripple and biogenic roughness. | off: no mobile sediment (d50 = 0.12 m never moves: Shields number < 1) |
| `SSW_LOGINT` + `SSW_LOGINT_WBL` or `SSW_LOGINT_DIRECT` (`sg_zwbl`) | interpolates the bottom-cell velocity logarithmically to a reference height: the top of the wave boundary layer (Madsen 1994), or a user height. Without it the stress uses the bottom cell's own height, 3 cm on the crest, inside the wave boundary layer | **`SSW_LOGINT_WBL`**: the Madsen model is written for the current at the top of the wave boundary layer, and that height changes with the waves |
| `SSW_LOGINT_STOKES` | automatic with `WEC`: the near-bed reference velocity excludes the Stokes drift. | automatic |
| `SSW_CALC_UB` | ROMS computes the bottom orbital velocity from Hs and the bottom period instead of taking SWAN's spectral `UBOT`/`Uwave_rms`. | off: SWAN's spectral value is better (COAWST uses Urms since rev. 393) |
| `SSW_FORM_DRAG_COR` | adds bedform form drag to the stress. | off (no bedforms) |
| `BEDLOAD_VANDERA_*` | sediment only. | off |

**The bottom-stress cap and its alternatives.** ROMS applies the stress
explicitly (a flux into the bottom layer in `pre_step3d.F`, and as a
frozen forcing of the barotropic mode). On a crest 0.3-0.5 m deep with 10
levels the bottom layer is 3-5 cm thick and the explicit stress is only
stable if |tau_b| <= 0.75 Hz_1 |u_1| / DT (`LIMIT_BSTRESS`). The cap binds
whenever Cd |u_1| exceeds 0.75 Hz_1 / DT, i.e. above about 0.6 m/s on
A15 at DT 6 s and over most of the realistic case's crest jet (98 % of
the points with |vbar| > 0.8 m/s in a 4-h run; the friction there was
about 5x below the log law, notebook 2026-10-27). Three
ways out:

| Choice | Pros | Cons | Status |
|---|---|---|---|
| explicit, uncapped (neither option) | the plain ROMS stress; on A15 at DT 6 s it is stable and its integrals (lagoon set-up, crest transport) are converged in DT (6, 3 and 1.5 s identical, notebook 2026-10-27) although the nominal stability number on the crest is 1.15 | would fail on a faster, shallower crest (every run of the realistic case needs one of the two options) | A15 as built |
| `LIMIT_BSTRESS` (cap) | always stable | friction too weak exactly where the jet is strongest; the realistic case's crest jet ran at 1.6-2.1 m/s instead of 1.1-1.3 | the realistic case's early runs |
| `BSTRESS_IMPLICIT` (needs `-SPLINES_VVISC`; engine patch, tier experimental) | full log-law stress at any layer thickness; drag inside the tridiagonal vertical solve like UCLA ROMS; converged in DT (A15 set-up DT 6 vs 3 s: 0.02 cm) and within 2.5 % of the explicit integrals where the cap does not bind | changes the vertical viscosity operator at the same time (splines off); results on fast crests differ from the capped runs by design (jet a third weaker, set-up 7-10 % lower, mean reef current -6 % in the realistic case's day runs, 2026-10-28) | the realistic case's default since 2026-10-28 on grids with a crest of at least 0.4 m and rx0 at most 0.2 (24 h runs, no failure); fails within 40 min on a grid with a 0.30 m crest and rx0 0.4. The engine document marks it "not recommended" on the strength of that grid; the later runs on the smoother grids are the better evidence |
| thinner cap via a shorter DT | the cap scales with 1/DT | costs run time, and the cap still binds at the jet | not pursued |

Recommendation: A15 keeps the uncapped explicit stress while it stays
stable (it is the converged reference), adds `LIMIT_BSTRESS` only for a
member that fails under stronger forcing, and uses
`BSTRESS_IMPLICIT -SPLINES_VVISC` as the realistic case does when the
crest jet itself is the quantity of interest (patchy canopies, 2 m waves,
a lower crest), comparing one member both ways. Any grid that runs the
implicit stress should also keep the crest-smoothing rule (crest >= 0.4 m,
rx0 <= 0.2) that made it run. Either way, state which stress a published
run used: the two differ measurably on the crest.

**Roughness, two routes, usually one or the other** (2026-10-20; softened 2026-11-03 by the author: a suggestion, not a rule, since a coral reef can be a rough bed and a canopy at once): (a) bottom
roughness z0 (= d50/12 in the initial file), also sent to SWAN as the
Nikuradse roughness KN = 30 z0, floored at 0.05 m by the coupler
(`Master/mct_roms_swan.h` lines 1065-1071) and used by SWAN's
`FRICTION MADSEN`; (b) canopy frontal area through `VEGETATION`, with the
plant fields sent to SWAN (`VEG_SWAN_COUPLING`), and then the coupler's
KN floor drops to 0.0015 m so the bare bed is nearly smooth. SWAN then
uses `max(ZO from ROMS, kn)` with `kn` from `FRICTION MADSEN [kn]`
(`waves_coupler.ftn` lines 2206-2225): the `0.3` in `swan.in` is a floor,
equal to the bare-bed value 30 x 0.01 m today, and it must be lowered to
the smallest intended KN whenever the roughness field has smoother
patches, or SWAN will never see them.
Spatial roughness: write `grain_diameter` per cell with the vegetation
pattern tools, or use `UV_DRAG_GRID` with `ZoBot` in the grid and
`SSW_CALC_ZNOT` off.

### 1.6 Vertical turbulence closure

| Closure | What it is | Verdict |
|---|---|---|
| `GLS_MIXING` | generic length scale two-equation model (Umlauf and Burchard 2003; Warner et al. 2005): k-epsilon, k-omega, k-kl (Mellor-Yamada 2.5 in GLS form) or "gen" by the `GLS_P/M/N` exponents in `ocean.in` | **use**, k-epsilon (`GLS_P` 3, `GLS_M` 1.5, `GLS_N` -1, `GLS_CMU0` 0.5477, `GLS_C1` 1.44, `GLS_C2` 1.92, `GLS_C3M` -0.4, `GLS_C3P` 1, `GLS_SIGK` 1, `GLS_SIGP` 1.3) as in every run so far |
| `MY25_MIXING` | the original Mellor-Yamada 2.5 code. | keep off: k-kl inside GLS is the same physics with the newer code path |
| `LMD_MIXING` (+ `LMD_SKPP`, `LMD_BKPP`, `LMD_NONLOCAL`, `LMD_RIMIX`, `LMD_CONVEC`, `LMD_DDMIX`, `LMD_SHAPIRO`) | K-profile parameterization: a diagnosed boundary-layer depth with a prescribed profile, built for wind- and convection-driven upper-ocean mixing. | keep off: no prognostic turbulence for a wave-breaking surf zone or a canopy, no coupling to the vegetation module |
| `BVF_MIXING` | diffusivity from the buoyancy frequency only. | off |
| `LIMIT_VDIFF`, `LIMIT_VVISC` (`AKT_LIMIT`, `AKV_LIMIT`) | upper caps on the mixing coefficients. | off; the 1e-3 values in `ocean.in` are inert without them |

GLS sub-options:

| Option | What it does | Verdict |
|---|---|---|
| `KANTHA_CLAYSON` / `CANUTO_A` / `CANUTO_B` | stability functions. Kantha and Clayson (1994) are quasi-equilibrium Galperin-type functions that shut mixing off above Ri about 0.2; Canuto A and B (2001) keep mixing to Ri about 1 and are derived differently (Living with ROMS section 6). Warner et al. (2005) found the closures and stability functions within each other's scatter in their tests | `KANTHA_CLAYSON` (every run so far). `CANUTO_A` is a **sensitivity** for the stratified cases (on the heated reef 2026-11-03: within 1-3 % of Kantha-Clayson; gen within 5 %; k-omega odd in the lagoon; k-epsilon, Kantha-Clayson and `VEG_TURB` on adopted by the author): it mixes more in weakly stable shear layers (the crest jet over the stratified lagoon) |
| `N2S2_HORAVG` | horizontal smoothing of the buoyancy and shear terms before they enter the production (4-point average). | on, except with `VEG_TURB`, where the headers switch it off so the canopy source stays local to the canopy cells |
| `RI_SPLINES` | spline reconstruction of the vertical shear. | on: better shear in uneven layers |
| `K_C2ADVECTION`, `K_C4ADVECTION` | centred advection of k and gls instead of the default U3 | off |
| `CHARNOK` (`CHARNOK_ALPHA` 1400) / `ZOS_HSIG` (`ZOS_HSIG_ALPHA` 0.5) | surface roughness length for the length-scale boundary condition: from the wind stress, or 0.5 Hs. Without either, `Zos_eff = max(Zos, 1e-4)` with `Zos` from `ocean.in` (0.5 m in both families: a fixed 0.5 m length scale at the surface) | **`ZOS_HSIG` to test**: it makes the surface length scale follow the waves (0.5 m offshore at Hs 1 m, 5-15 cm on the reef flat where Hs is 0.1-0.3 m), where the fixed 0.5 m is larger than the water depth on the crest |
| `CRAIG_BANNER` (`CRGBAN_CW` 100) / `TKE_WAVEDISS` (`SZ_ALPHA` 0.25) | surface TKE flux from breaking: Craig and Banner (1994) from the wind stress (cw u*^3), or from the wave model's breaking plus whitecapping dissipation (`Dissip_break + Dissip_wcap` times `SZ_ALPHA`), which `WDISS_WAVEMOD` supplies. Without either, the surface TKE is the wall-law value from the wind stress, i.e. `GLS_Kmin` with no wind (`gls_corstep.F` lines 916-935, 965-979) | **`TKE_WAVEDISS` to test**: at present the breaking waves push the crest flow (`WEC_VF`) but inject no turbulence into GLS, so the vertical mixing of the crest jet comes only from bottom shear. Surf-zone observations (Feddersen and Trowbridge 2005) put breaking-wave turbulence at the top of the budget. Expected effect: more vertical mixing in the surf zone on the crest and forereef, a less sheared cross-reef jet, faster erosion of stratification over the reef flat, and a different partition between surface-layer and depth-mean transport, which matters for larvae and heat. `CRAIG_BANNER` is wrong for us (no wind). It needs `WDISS_WAVEMOD`, already on |
| `SPLINES_VVISC` | spline reconstruction of the vertical viscous flux. | A15: on in the explicit-stress builds; off whenever `BSTRESS_IMPLICIT` is used (compile error otherwise). Prefer **off** in new builds of both families: the standard tridiagonal operator is what the implicit drag terms are built into, and it keeps the two stress schemes comparable |

GLS parameters worth a note (**A15 default `GLS_Kmin` 1e-8 since 2026-11-03**, the author's
decision after 72 h heated runs: stable, the same answer as 1e-10, quiet-water mixing then
set by `AKT_BAK`/`AKV_BAK`; `docs/gls_kmin.md`): `GLS_Kmin` 7.6e-6 m2/s2 is the k-epsilon
default; the Galperin length-scale limit then gives a floor of
AKt about 0.05 Kmin / N in stratified water (Living with ROMS section 6),
3.8e-5 m2/s at N^2 = 1e-4, 8x `AKT_BAK` 5e-6. For the stratified
offshore column this is a small, uniform extra mixing; lowering `GLS_Kmin`
to 1e-8 or 1e-10 recovers the background values but k-epsilon is then
less forgiving (forum reports of instability). Low priority; a
**sensitivity** for week-long stratified runs. Unexplained so far: the
2 m backreef at rest shows AKt about 1e-3 m2/s (`case_design.md`,
constant stratification), 20x the offshore floor; the candidates are the
canopy source and GLS in very shallow water. Worth one diagnostic run with
`VEG_TURB` off before the encyclopedia runs, because it sets how fast the
reef flat destratifies.

Surface wind roughness options that only matter with `BULK_FLUXES`
(`COARE_TAYLOR_YELLAND`, `COARE_OOST`, `DRENNAN`, `DEEPWATER_WAVES`) are
in section 1.9.

### 1.7 Vegetation (coral canopy)

COAWST's vegetation module (Beudin et al. 2017; Kalra et al. 2017) models
rigid or flexible cylinders of diameter D, height h, density n per m2 and
thickness t, with drag, turbulence and wave dissipation.

| Option | What it does | Verdict |
|---|---|---|
| `VEGETATION` (+ `NVEG`, `vegetation.in`) | the module; plant fields from the initial file (`ANA_VEGETATION` for analytic ones). | on in the canopy cases |
| `VEG_DRAG` (`CD_VEG` 1.0) | drag 0.5 Cd D n \|U\| U in every layer inside the canopy, explicit (AB3) in the 3-D equations and as a frozen forcing of the barotropic mode. | on. Explicit drag is stable only while 2 alpha \|U\| DT (alpha = 0.5 Cd D n) stays near or below 1: A15 patchy needed DT 3 s (6 s blew up at 42 min), the realistic case's patchy canopy blew up at DT 4 s (`case_design.md`, spatially varying vegetation) |
| `VEG_DRAG_IMPLICIT` (engine patch, experimental tier) | the same drag taken backward Euler inside the vertical solve and at every fast step: no time-step limit. | **use for patchy or dense canopies** (decided 2026-10-27): A15 patchy at DT 6 s stayed within 1 cm/s of the explicit DT 3 s run at 99.9 % of cells; the realistic case's patchy day run clean. Keep explicit for sparse uniform canopies if continuity with old runs matters; the two agree to 1-2 % where both run |
| `VEG_TURB` | canopy turbulence (Uittenbogaard 2003): TKE and dissipation sources from the drag work, with the canopy time scale `tau_veg` set by the gap between plants L = c_l sqrt((1 - D t n)/n). | on. Two user conventions: `plant_thickness = (pi/4) D` so D t is a cylinder's cross-section (D t n = 1 gave L = 0 and a division by zero on 2026-10-21); `tau_free` off, as shipped in v3.9 (the published min(k/epsilon, tau_veg) cut canopy eddy viscosity 65 % in the A15 test; to revisit with field data). The engine's `roms-vegetation` fix corrects the units of `tau_veg` (canopy eddy viscosity about 10 % lower), the periodic crash, the v-point drag average and stops when D t n >= 1 |
| (note) `VEG_TURB` with other GLS closures | its source is added to the length-scale variable as an epsilon source (`gls_c2 P_veg / tau`), correct only for k-epsilon | k-epsilon adopted 2026-11-03, so no patch is needed; if k-omega, gen or k-kl is ever chosen, port the source to the generic psi equation first |
| `VEG_FLEX` (`E_VEG`, `VEG_MASSDENS`) | flexible blades: effective height reduced by bending (stiffness D t^3/12). | **off**: corals are rigid; the formula is for flat blades |
| `VEG_SWAN_COUPLING` | ROMS sends plant density, height, diameter and thickness to SWAN every exchange; SWAN dissipates waves on them (`VEGETATION 3`, section 3). The coupler's KN floor drops from 0.05 to 0.0015 m. | **on with the canopy route**: the same canopy must take wave energy and current momentum; without it SWAN would see a bare bed with KN 0.3 m. `swan.in` still needs `INPGRID NPLANTS` (no `READINP`) or SWAN ignores the coupled density (`case_design.md`) |
| `VEG_STREAMING` | wave-induced streaming force inside the canopy (Luhar et al. 2010). | **on in the A15 canopy cases since 2026-11-03** (author): with the coawst-cloud fix `roms-veg-streaming-fixes` (the stock force replaced the bottom streaming, was not normalized, had no ghost points, and its restart variable lacked the record dimension); with `BOTTOM_STREAMING` the lagoon set-up +95 %, crest transport +32 %, stable at DT 6 s. Acts only together with `BOTTOM_STREAMING` |
| `VEG_HMIXING` | see section 1.2. | **to test** with patchy canopies |
| `MARSH_*`, `VEG_BIOMASS`/`SAV_BIOMASS`, `ESTUARYBGC`, `SPECTRAL_LIGHT` | marsh dynamics, biomass growth, estuarine biogeochemistry. | not for us |

Choosing coral parameters: match frontal area D h n (drag) and bed
coverage pi D^2 n / 4 (gap, turbulence) separately; the classes in use are
sparse n 1 m-2 and dense n 4 m-2, D 0.5 m, h 0.4 m, Cd 1 in both models.

### 1.8 Waves on currents (WEC)

| Option | What it does | Verdict |
|---|---|---|
| `WEC_VF` | vortex-force formalism (Uchiyama et al. 2010; Kumar et al. 2012): Stokes drift advects momentum and tracers, vortex force, Bernoulli head and quasi-static pressure, breaking and roller body forces. `WEC_MELLOR` (radiation stresses) is gone from the v3.9 source; the `#undef WEC_MELLOR` in the headers is a leftover | **use** |
| `WDISS_WAVEMOD` / `WDISS_THORGUZA` / `WDISS_CHURTHOR` | where the breaking dissipation comes from: SWAN (`DISSURF`), or ROMS's own Thornton-Guza or Church-Thornton formula from Hs and depth. | **`WDISS_WAVEMOD`**: SWAN computes the breaking that also shapes its own wave field; a second formula in ROMS would be inconsistent with it |
| `DISSIP_BREAK_DIR` | breaking force from x and y dissipation components instead of the scalar times the mean direction. | **do not use with SWAN**: only the WW3 coupler fills `Dissip_breakx/y`; with SWAN the arrays are never set (`Master/mct_roms_swan.h` fills `Dissip_break` only). A pity for cases with crossing wave trains; the mean direction `Dwave` is what we have |
| `WEC_ALPHA` (`ocean.in`, 0) | fraction of the breaking dissipation routed to the roller instead of the direct force. | 0 (no roller) |
| `ROLLER_SVENDSEN`, `ROLLER_MONO`, `ROLLER_RENIERS` | surface roller: part of the breaking energy is stored in a roller and released a few wavelengths shoreward, shifting the set-up and the longshore current onshore (Reniers is the suggested one). | **sensitivity** for the reef flat: on a 50-100 m wide reef surf zone the roller lag moves where the momentum lands (onto the reef flat rather than the forereef), which changes the cross-reef set-up gradient and the crest jet. No run yet; needs `WEC_ALPHA` > 0 and the roller restart fields were not part of the restart tests |
| `BOTTOM_STREAMING` (+ `_YU` default, `_XU_BOWEN`), `SURFACE_STREAMING` | wave-boundary-layer streaming force near the bed (onshore), and surface streaming. | **on in all A15 cases since 2026-11-03** (author): on the canopy reef bottom friction takes 34 % of the wave dissipation (crest and top of the fore reef, Madsen f_w 0.25-0.3), comparable to breaking (40 %); the force carries that momentum: set-up +57 %, crest transport +22 %, stable at DT 6 s with `BSTRESS_IMPLICIT` (an explicit-drag case blew up) |
| `WAVE_MIXING` | extra vertical viscosity from breaking (Uchiyama et al. 2010), independent of GLS. | keep off; `TKE_WAVEDISS` (section 1.6) does the same job inside the closure |
| `BULK_STOKES` / `SPECTRUM_STOKES` | Stokes drift profile from bulk Hs, T, L, or summed over SWAN's frequency bins (Liu et al. 2021). `SPECTRUM_STOKES` is automatic with SWAN unless `BULK_STOKES` is defined. | **`SPECTRUM_STOKES`** (decided 2026-10-21): the bulk profile from the peak period is too deep for a broad spectrum. Cost 15x the bulk kernel before the engine's `roms-wec-stokes-fast` patch, about 5x after; the `roms-wec-stokes-fixes` patch is required (the stock u-point loop was wrong) |
| `UV_KIRBY` / `UV_BANIHASHEMI` / `UV_CONST` / none | the current sent to SWAN for refraction and Doppler shift: depth weighted over the wave's own depth (Kirby and Chen 1989), per wave number (Banihashemi et al. 2017), zero, or the surface current. | **`UV_KIRBY`**. `UV_BANIHASHEMI` (one current per frequency bin, for strongly sheared currents such as the undertow under the crest jet) was **tested 2026-11-03** on A15: within 0.5 % of `UV_KIRBY` (fore-reef shear ratio +5 %), wall time +5 %: no practical difference. It replaces `UV_KIRBY` (`-UV_KIRBY +UV_BANIHASHEMI`); defining both does not compile. **Note for later:** consider switching to it, and check whether it is needed on every new domain: it matters where a strongly sheared current (an ebb jet or plume over a weaker or opposing lower layer, a wind-driven surface current over a return flow) meets a spectrum spanning kD < 1 and kD > 1 (deeper water, short wind waves), not on a shallow reef flat where every bin sees the depth mean; test it as one member against `UV_KIRBY` |
| `ZETA_CONST`, `SST_CONST` | send zero sea level or no SST. | off |
| `WEC_BREAK_UNIFORM` (engine patch) | breaking force spread evenly over depth instead of the cosh profile (ratio top/bottom 188 on A15's crest). | **sensitivity** only: it changes surface currents by up to 14 cm/s on A15; it did not cure the realistic case's crest blow-up |
| `FLOATS_STOKES`, `FLOATS_WINDS` | add Stokes drift (and 1 % of the wind) to online float velocities. | only with `FLOATS` (section 1.11) |

Note on the vertical profile of the breaking force: `wec_vf.F` spreads the
depth-integrated force as cosh(2 pi gamma (z - z_b)/D) with gamma =
min(1.414 D / (1.25 Hs), 1), so where Hs is comparable to the depth (the
crest) nearly all of it goes into the top layers. That is the standard
surf-zone assumption; on a 0.5 m crest with 5 cm layers it concentrates
the forcing in the top 1-2 cells, which is where the implicit-stress
failures on the realistic case's steepest grid showed up. `WEC_BREAK_UNIFORM` exists to
check how much depends on it.

### 1.9 Surface forcing, tides and rivers

| Option | What it does | Verdict |
|---|---|---|
| `ANA_SMFLUX` | analytic wind stress (zero in both families). | on until winds are forced |
| `ANA_STFLUX`, `ANA_SRFLUX`, `ANA_SSFLUX` | analytic heat, shortwave and freshwater fluxes; the `_therm` cases carry their own `ana_stflux.h`/`ana_srflux.h`: clear-sky diurnal shortwave plus a non-solar flux with a linear SST feedback (40 W/m2/C about 28 C) | **use now** (decided 2026-10-23). A constant non-solar flux let stagnant nearshore water reach 42 C; the feedback caps it |
| `BULK_FLUXES` (+ `COOL_SKIN`, `LONGWAVE` or `LONGWAVE_OUT`, `EMINUSP`, `ALBEDO`, `DIURNAL_SRFLUX`, `WIND_MINUS_CURRENT`) | COARE bulk formulae from air temperature, humidity, wind, cloud: latent, sensible and longwave fluxes respond to the model SST. `WIND_MINUS_CURRENT` uses the wind relative to the surface current. | **the planned upgrade** for the thermal cases: a physical SST feedback instead of the 40 W/m2/C constant, evaporation, and a wind that also drives the flow and SWAN's `WIND` growth. With it: `WIND_MINUS_CURRENT` on (currents of 1 m/s against trade winds of 5-8 m/s change the stress by 20-40 %), `LONGWAVE_OUT` if downwelling longwave is given, `ALBEDO` with cloud, `COOL_SKIN` optional. Arango's warning (Living with ROMS section 4): bulk fluxes with radiation open boundaries can go unstable at the boundary; our boundary is nudged to a far field, which is the usual cure. The far-field column tool then needs the same formulae |
| `COARE_TAYLOR_YELLAND`, `COARE_OOST`, `DRENNAN`, `DEEPWATER_WAVES` | sea-surface roughness for the wind stress from the wave height and age (SWAN's Hs, Lp). | with `BULK_FLUXES` and waves, `COARE_TAYLOR_YELLAND` is the common choice; one of them is a **sensitivity** on the wind stress, not on the circulation |
| `ATM_PRESS`, `ANA_PAIR` | inverse barometer. | off |
| `ANA_FSOBC`, `ANA_M2OBC` | analytic sea level and 2-D momentum at the open boundary: the case tide (amplitude and period as `USER` parameters). | **use**; the `Shc` 2-D condition takes the sea level from here |
| `SSH_TIDES`, `UV_TIDES`, `RAMP_TIDES`, `ADD_FSOBC`, `ADD_M2OBC`, `FSOBC_REDUCED`, `TIDE_GENERATING_FORCES` | harmonic tidal forcing from a tide file (elevation and currents), ramped over a day, added to boundary data; reduced-physics 2-D boundary; body tide. | for a realistic tide (constituents from a global model) switch to `SSH_TIDES` + `UV_TIDES` + `RAMP_TIDES` with `Cha`/`Fla` boundary conditions (section 1.10). Not needed for the idealized single-constituent tide. `TIDE_GENERATING_FORCES` is negligible at these scales |
| `LuvSrc` (face sources), `LwSrc` (volume sources), `LtracerSrc`, `ANA_PSOURCE` | rivers as momentum through a face or as a volume source in a cell; tracer concentrations; vertical shape `Vshape`. | **face sources with the water in the top 1 m** (decided 2026-10-29 for the realistic case): like ROMS's river tests; both kinds restart exactly after the engine's `roms-restart-wec` fix |
| `ANA_INITIAL`, `ANA_GRID`, `ANA_MASK` | analytic initial state, grid, mask. | off (files) |

### 1.10 Lateral boundary conditions

Set per variable and edge in `ocean.in` (`LBC(...)`); both families are
periodic in i (`Per`), closed on the inner edge (`Clo`: A15's south wall),
and open on the outer edge (A15's north).

| Keyword | What it is | Verdict for the open edge |
|---|---|---|
| `Che` / `Cha` | Chapman explicit/implicit for the free surface: the sea level radiates at sqrt(gh) toward the imposed exterior value. | **`Che`** for zeta with the analytic tide; `Cha` with `SSH_TIDES` |
| `Shc` | Shchepetkin condition for 2-D momentum: a Flather-type condition that takes the exterior sea level and lets gravity waves out (its role, in Shchepetkin's words, is to stop seiches from being trapped; Living with ROMS section 17.4). | **`Shc`** for ubar, vbar (every run so far) |
| `Fla` | Flather for 2-D momentum from exterior sea level and currents. | with a tide file that has currents (`UV_TIDES`) |
| `Red` | reduced physics for 2-D momentum (pressure gradient, Coriolis, stresses only). | when only elevation is known and `Shc` misbehaves |
| `Rad`, `RadNud` (+ `TNUDG`, `M3NUDG`, `OBCFAC`) | Orlanski-type radiation for 3-D momentum and tracers; `RadNud` adds relaxation to an exterior state (inflow time scale = outflow / `OBCFAC`: 1 day outflow, 0.1 day inflow with `OBCFAC` 10). | **`RadNud`** for u, v, T, S (decided 2026-10-23): over 24 h with the zero-gradient condition the boundary error grew to 2 C and reached the reef; `Rad` and `RadNud` both held it to 0.1-0.2 C, and `RadNud` with the nudging band to 0.03 C; over 3 days with heating only `RadNud` plus the band kept the far field right, because the wave-driven overturning imports heat that `Rad` lets accumulate (`case_design.md`, thermal forcing) |
| `Gra` | zero gradient. | **`Gra` for TKE/GLS and for the Stokes variables** on the open edge (Arango: radiation on TKE is unwise, Living with ROMS section 17.6); never for tracers at a stratified open boundary (the error above). Housekeeping: A15's `ocean.in` still has `Gra Clo Gra Gra` for the Stokes and wave-action variables while every other variable is `Per Clo Per ...`; ROMS skips the west/east conditions on a periodic grid, so it is harmless, but set them to `Per` |
| `Cla` | clamped to the exterior value. | not for an outflow edge |
| `Clo`, `Per`, `Nes` | closed wall, periodic, nested. | as above |
| `RADIATION_2D` | oblique radiation (tangential phase speed). | off: the open edge is far from the reef and nudged |
| `IMPLICIT_NUDGING` | implicit treatment of the `RadNud` momentum nudging. | off; worth turning on if inflow nudging is ever made strong (time scales below an hour) |
| `VolCons(...)` | global volume conservation at open edges. | off: not with tides (glossary), not with periodic edges (Living with ROMS section 17.1) |
| interior nudging band: `Lm3CLM`, `LtracerCLM`, `LnudgeM3CLM`, `LnudgeTCLM`, `NUDNAME`/`ANA_NUDGCOEF`, `CLMNAME`/`ANA_TCLIMA`, `ANA_M3CLIMA` | relaxes interior points near the edge toward a reference (the initial stratification, or the far-field column of `tools/thermal/far_field.py`), 1-2 km wide, 1 h at the edge. | **on** in every stratified and thermal case (decided 2026-10-23). Read the reference from files (`CLMNAME`, `BRYNAME`) rather than from analytic routines that copy the state on their first call, so that restarts keep it |
| `LsshCLM`, `Lm2CLM`, `LnudgeM2CLM` | nudging of sea level and 2-D momentum. | **never nudge the free surface** (Arango, Living with ROMS sections 16-17): it breaks volume conservation; force through ubar/vbar if at all |

### 1.11 Output and run control

| Option | What it does | Verdict |
|---|---|---|
| `PERFECT_RESTART` | restart files with the extra time levels so a restarted run continues bit for bit. | **on**: Spot segments depend on it; with the engine's `roms-restart-wec`, `roms-restart-step-count` and `swan-exact-restart` fixes it is exact with waves, GLS, rivers and vegetation. `DSTART` 730119 keeps the step counter from overflowing at DT 2 s |
| `AVERAGES`, `NAVG`, `NTSAVG` | time-averaged history. | on: averages are what the ensemble statistics and the particle tracking read (10-min averages for tracking) |
| `AVERAGES_DETIDE` | detided averages (least-squares harmonic). | off |
| `DIAGNOSTICS_UV`, `DIAGNOSTICS_TS` | momentum and tracer term balances. | on only for the members where a budget is wanted: 0.82 GB per simulated day on A15, 29 % of the output |
| `STATIONS` (`STATIONS_CGRID`) | time series at points. | **to use** for high-frequency reef-flat records (wave set-up, temperature at the crest and lagoon) without hourly 3-D files |
| `FLOATS` (+ `FLOAT_VWALK`, `VWALK_FORWARD`, `FLOAT_STICKY`, `FLOATS_STOKES`, `FLOATS_WINDS`, `FLOAT_OYSTER`) | online Lagrangian drifters, RK4 on the model fields every step, with vertical random walk from AKt and Stokes drift. | off: particle tracking is offline with ROMSPath (decided), which reads 10-min averages and can be rerun with different behaviours. Online floats would be the check that 10-min averages are frequent enough (one member, same release) |
| `OUT_NETCDF4`, `DEFLATE` | NetCDF-4 with lossless compression. | on (engine default): 2-4x smaller files, 1-2 % run time |
| `OUT_DOUBLE` | double-precision output. | off (single is enough for analysis; restarts are double anyway) |
| `RST_SINGLE` | single-precision restarts. | **off**: exact restarts need double |
| `WRITE_WATER`, `READ_WATER` | water points only. | off (tools expect full grids) |
| `PARALLEL_IO`, `PIO_LIB`, `PNETCDF` | parallel I/O. | off: output is a small share of the run |
| `CHECKSUM`, `OUTPUT_STATS`, `CHECK_OPEN_FILES`, `METADATA_REPORT` | diagnostics in the log. | off except when debugging |
| `ROMS_STDOUT` | log to `log.roms`. | off (stdout is captured) |
| `DEBUGGING` | omit the date and options from file headers (for binary comparisons). | off (compare by value) |
| `NO_WRITE_GRID` | no grid arrays in output. | off |

### 1.12 Options that are not for these cases

Listed so that the catalogue is complete; all stay off.

- **Sediment**: `SEDIMENT`, `SUSPLOAD`, `BEDLOAD_MPM`/`_SOULSBY`/`_VANDERA` (+ the van der A sub-options), `SED_MORPH`, `COHESIVE_BED`, `MIXED_BED`, `NONCOHESIVE_BED1/2`, `SED_FLOCS`, `SED_DEFLOC`, `FLOC_*`, `SED_BIODIFF`, `SED_DENS`, `SED_TAU_CD_*`, `SED_SLUMP`. The engine's `roms-sed-morph-tiling` and `roms-vandera-no-sand` fixes matter only if sediment is turned on.
- **Biology**: `BIO_FENNEL`, `ECB`, `HYPOXIA_SRM`, `NPZD_*`, `BIO_UMAINE`, `ECOSIM`, `NEMURO`, `RED_TIDE` and their sub-options.
- **Sea ice**: `ICE_*`.
- **Data assimilation, adjoint, GST**: every `*4DVAR*`, `AD_*`, `TL_*`, `RP_*`, `*_DRIVER`, `OPT_*`, `HESSIAN_*`, `SO_*`, `FULL_GRID`.
- **Other couplings**: `WRF_MODEL`, `WRF_COUPLING`, `ATM2OCN_FLUXES`, `WAV2OCN_FLUXES` (WW3 only), `Z0_WAV_SIN`, `Z0_PORCHETTA`, `DRAGLIM_DAVIS`, `WW3_MODEL`, `INWAVE_MODEL` and the InWave options, `ESMF_LIB`, `CICE_COUPLING`, `COAMPS_COUPLING`, `REGCM_COUPLING`, `WAM_COUPLING`, `REFDIF_COUPLING`, `DATA_COUPLING`, `FRC_COUPLING`, `TIME_INTERP`, `WRF_TIMEAVG`, `EXCLUDE_SPONGE`.
- **Nesting**: `NESTING`, `ONE_WAY`, `REFINE_BOUNDARY`, `TIME_INTERP_FLUX`, `NO_CORRECT_TRACER`, `NESTING_DEBUG`, `MCT_INTERP_*` (section 5).
- **MPI communication variants**: `ASSEMBLE_ALLGATHER/ALLREDUCE`, `COLLECT_ALLGATHER/ALLREDUCE`, `REDUCE_ALLGATHER/ALLREDUCE`, `BOUNDARY_ALLGATHER`: the default low-level sends are fine on one VM; a benchmark would only matter on a multi-node cluster.

## 2. ROMS numerics (cpp and `ocean.in`)

### 2.1 Vertical grid

| Parameter | Choice | Why |
|---|---|---|
| `N` | **15 on A15 since 2026-11-03** (author; N 10 was not converged: set-up -7 % at N 15, -10 to -12 % at N 20, which needs DT 3 s); 10 before | enough to resolve a log layer, the surface heating layer and the Stokes drift profile offshore; on the crest it gives 3-5 cm layers, which is already the thinnest the explicit bottom stress tolerates. 20 levels made the realistic case's implicit-stress runs fail earlier (thinner surface layer under the concentrated breaking force, notebook 2026-10-27), raises rx1 and the pressure-gradient error, and roughly doubles cost. If vertical structure on the reef flat is ever the target, raise `N` together with the crest-smoothing rule and a new rest test |
| `Vtransform` 2, `Vstretching` 4 | the modern transformation (Shchepetkin 2005) and the double-stretching function | the ROMS recommendation; in water shallower than `TCLINE` the layers are near-uniform, which is what the crest needs |
| `THETA_S` 3, `THETA_B` 2, `TCLINE` 20 m | moderate surface and bottom refinement below 20 m | resolves the surface heated layer and the bottom boundary layer offshore without thinning the crest layers. Shchepetkin's forum rule (Living with ROMS section 14.1): coarser vertical resolution and surface-concentrated stretching tolerate steeper topography, so do not raise `THETA_B` on steep slopes |
| rx0, rx1 | A15 about 0.15 / small (the realistic case: rx0 0.15, rx1 2.8) | the crest-smoothing rule (crest >= 0.4 m, rx0 <= 0.2) is a numerics requirement for the implicit bottom stress and for the pressure gradient; keep it in the grid generators |

### 2.2 Time steps

ROMS has a baroclinic step `DT` and `NDTFAST` barotropic sub-steps of
`DT/NDTFAST`.

| Limit | How it binds here | Rule |
|---|---|---|
| barotropic Courant number, sqrt(gh) dt_fast sqrt(1/dx^2 + 1/dy^2), reported by ROMS at start-up | 400 m deep A15 boundary at 20 m cells: 0.81 at DT 6 s / NDTFAST 24 (the realistic case: 0.88 at DT 4 s / NDTFAST 21) | keep it at 0.8-0.85: the LF-AM3 limit is about 0.9, AB3-AM4's 0.890 (linear analysis, `tools/fb_stability.py`; Shchepetkin quotes 0.87); "anything less than 0.8 is a waste" (Shchepetkin), but 0.885 was "too close" on the realistic case and NDTFAST went from 16 to 17 |
| vertical advective Courant number in the thin crest layers | the real limit on `DT`: A15 at DT 6 s is fine for Hs 1 m; the realistic case (10 m cells, 0.3-0.5 m crest) needs DT 4 s (6 s blew up after 1.6 h, Cw 2-10 at the crest), and 2 s at Hs 2 m (Cw passed 1 at 4 s and the run blew up when the waves reached full height, notebook 2026-10-29) | halve `DT` when `Cw` in the log approaches 1; `OMEGA_IMPLICIT` is not a substitute (section 1.2) |
| internal-wave Courant number, c1 DT / dx with c1 = N H / pi | A15 at N^2 = 1e-4, DT 6 s: 0.39 (fine); 3e-4: 0.68 (blew up at 34 min), 3 s: 0.34 (fine) | keep below 0.4-0.5 (`tools/cfl_check.py`); the limit adds to the advective one (Shchepetkin). Where it binds is the deepest water on the narrowest columns next to the open boundary |
| explicit canopy drag, 2 alpha \|U\| DT | patchy A15: 1.0 at 6 s and growing (blew up), 1.26 at 3 s (ran) | DT 3 s for patchy explicit canopies, or `VEG_DRAG_IMPLICIT` |
| explicit bottom stress | always capped (`LIMIT_BSTRESS`) or implicit | - |
| `NDTFAST` too small | an A15 attempt at DT 1 s with NDTFAST 4 ran away in the surface layer: too few fast steps for the barotropic time averaging | keep `NDTFAST` at 15 or more; Arango's "larger than 30" (Living with ROMS section 9) is for coastal grids with long baroclinic steps, where the averaging filter needs the room |

Chosen values: A15 DT 6 s, NDTFAST 24 (3 s and 12 when the canopy or
stratification limits bind); the realistic case DT 4 s, NDTFAST 21 (2 s
and 11 at Hs 2 m, which doubles the cost).

### 2.3 Barotropic kernel

| Option | Scheme | Verdict |
|---|---|---|
| default | LF-AM3 predictor-corrector: two kernel calls per fast step plus an auxiliary step; the legacy Rutgers scheme | A15's reference scheme so far |
| `STEP2D_FB_AB3_AM4` (engine patch `roms-step2d-fb`, experimental tier) | generalized forward-backward AB3-AM4 (Shchepetkin and McWilliams 2005, section 2.3; what UCLA ROMS uses): one call per fast step, stable to Courant 0.89. Stock v3.9 ships it unfinished and never compiles it; the patch completes it with the wave and vegetation terms | **the realistic case's default**: 18 % faster with 20 + 12 processes (6 h test), results within 4 mm of sea level and 2 cm/s of LF-AM3; the engine's test shows it as close as LF-AM3 to a 4x-smaller-step reference on A15 and Circle_Island, with the 2-D kernel 2.4-2.6x cheaper. **For A15 it is a free choice**: the kernel is 32 % of ROMS time there, so expect 5-15 % per run; switch the whole ensemble at once so that members stay comparable |
| `STEP2D_FB_LF_AM3` | LF-AM3 with forward-backward feedback. | not compiled in v3.9 either; skip |
| `STEP2D_CORIOLIS` | Coriolis inside the 2-D kernel in 3-D set-ups. | off (the patch recomputes the 2-D advection, Coriolis and vortex-force terms every fast step as LF-AM3 does; freezing them in the 3-D forcing, the Rutgers/UCLA design, let a shallow crest column go unstable at low tide) |

### 2.4 Tiling and process layout

- `NtileI x NtileJ` must equal `NnodesOCN`. 1 x N tilings (strips across
  the alongshore direction) give bit-identical results for any N; i-splits
  differ at rounding level because of the WEC terms (`case_design.md`).
  Tile shape barely changes speed except very thin strips across x
  (A15 10 x 1: 13 % slower).
- Balance: with `SWAN -O3` the split 10 ROMS + 6 SWAN on 16 vCPUs (A15)
  keeps ROMS from waiting for SWAN (about 1 SWAN process per 2 ROMS). C2D
  (AMD) machines were 25-30 % faster than C3D at every split for A15;
  hyperthreads help a little on C2D.
- SWAN's own decomposition is forced to y-strips by the engine's
  `swan-periodic-fixes` (x-strips broke the periodic wrap), so the number
  of SWAN processes is limited by the number of rows.
- `NghostPoints` is 3 with MPDATA (automatic).

### 2.5 Other numerics switches

| Option | What it does | Verdict |
|---|---|---|
| `SPLINES_VDIFF`, `SPLINES_VVISC` | see sections 1.4 and 1.6 | `VVISC` off, `VDIFF` on (inert with MPDATA) |
| `RI_SPLINES`, `N2S2_HORAVG` | see 1.6 | on, on (off with `VEG_TURB`) |
| `TS_MPDATA_LIMIT` | see 1.4 | off |
| `INITIALIZE_AUTOMATIC` | zero the automatic arrays in `step2d` (a debugging aid). | off |
| `SINGLE_PRECISION` | 32-bit kernel. | off |
| `BVF_BAK`, `AKV_BAK`, `AKT_BAK`, `AKK_BAK`, `AKP_BAK` | background vertical mixing (5e-5 m2/s momentum, 5e-6 tracers and GLS). | keep; molecular-ish backgrounds, below the GLS floor of section 1.6 |
| `RHO0` 1025, `R0` 1027, `T0`, `S0`, `TCOEF`, `SCOEF` | Boussinesq reference and the linear equation of state. | `TCOEF` 3.2e-4 (28 C), `SCOEF` 7.6e-4 |
| `DCRIT` 0.10 m | wet/dry threshold. | only with `WET_DRY` |
| `GAMMA2` | slip condition at walls (1 free slip, -1 no slip). | 1 (free slip at the masked land; the no-slip wall stress COAWST adds with `WET_DRY` is separate) |
| `LEVSFRC`, `LEVBFRC` | body-force layers. | unused |
| `NINFO` | diagnostics interval; `NINFO = 1` checks for bad values every step and writes a restart when it blows up (Living with ROMS section 3). | 1: cheap, and the blow-up records are what made the crest diagnoses of the realistic case possible |
| `NRST`, `LcycleRST` | restart interval and cycling. | hourly, `LcycleRST F` kept every record (1.24 GB/day on A15); set `LcycleRST T` for production and rely on the segment runner |
| `NHIS`, `NAVG`, `NQCK`, `NDIA` | output intervals. | hourly history and averages; 10-min quicksaves (`NQCK`) for movies and tracking |

## 3. SWAN physics (`swan.in`)

SWAN's options are run-time commands. The defaults below are the ones the
bundled source actually applies (subroutine `SWINIT` in `swanmain.ftn`
and the parser in `swanpre1.ftn`), cross-checked against the 41.51 user
manual; the full command-by-command catalogue with line references is in
`docs/options/swan_command_catalogue.md`. Note that the bundled SWAN
reports version 41.51 but carries code tagged up to 42.15/43.02, so a few
commands exist that the 41.51 manual does not describe.

Current `swan.in` physics, A15: `GEN3`, `FRICTION MADSEN 0.3`,
`OFF QUAD`, `BREAKING CON 1.0 0.73`, `TRIAD`, `VEGETATION 3 0.4 0.5 1 1`
(canopy cases).

### 3.1 Generation mode and wind

| Command | What it does (source default) | Verdict |
|---|---|---|
| `GEN3` with no keyword | third generation with the Van der Westhuysen (2007) saturation whitecapping and Yan wind input (`WESTH` is the default, not `KOMEN`); `DRAG WU`. Wind input is zero without a `WIND` command or wind grid | **use**. Without wind the only active part is the saturation whitecapping, which on a 1 m / 10 s swell (steepness 0.006) is negligible; it does no harm and will be needed with winds |
| `GEN3 KOMEN`, `GEN3 JANSSEN` | the WAM cycle 3 and 4 formulations. | keep off; when winds arrive, `WESTH` is the SWAN team's default and avoids the known 10-20 % period underestimate of `KOMEN` |
| `GEN3 ST6 ...` | observation-based (Babanin) input and dissipation, with its own drag and swell dissipation. | not needed for a fetch of a few kilometres |
| `GEN1`, `GEN2` | parametric first and second generation (no quadruplets, no whitecapping). | off |
| `WIND [vel] [dir]`, `INPGRID WIND` | uniform or gridded wind for wave growth. | off until winds are forced; then the same wind as ROMS's stress (`BULK_FLUXES`) so that the two models see one atmosphere |
| `AGROW [a]` | linear (Cavaleri and Malanotte-Rizzoli) growth so waves can start from zero. | off |
| `SSWELL`, `NEGATINP`, `GEN4` | swell dissipation for ST6; negative wind input; the quasi-coherent research mode. | off |
| `DRAGLIM_DAVIS` (cpp) | caps the Wu drag at 2.4e-3 (the manual says 2.85e-3). | off (no wind) |

### 3.2 Whitecapping and quadruplets

| Command | What it does | Verdict |
|---|---|---|
| `WCAPPING` (default `AB`, i.e. the saturation form of `WESTH`), `KOMEN`, `JANSSEN`, `AB ... CURRENT` | deep-water steepness dissipation; the `CURRENT` extension (Van der Westhuysen 2012, undocumented in 41.51) adds dissipation on opposing currents. | leave at the `GEN3` default. `AB ... CURRENT` is **to test** wherever an ebb jet of 1-2 m/s opposes 10 s swell (reef passes): without it SWAN is known to overestimate Hs on blocking currents |
| `QUADRUPL` / `OFF QUAD` | four-wave interactions (DIA). COAWST forces `IQUAD = 3` (per-iteration integration) whenever currents are present, which doubles the interaction memory; and `OFF QUAD` also disables the action limiter (`PNUMS(20) = 1e20`) unless `NUM ... [limiter]` re-sets it | **`OFF QUAD`** (every run so far): the DIA moves energy between swell components over hundreds of kilometres of fetch; across a 5-10 km domain it changes nothing measurable and costs 20-30 % of SWAN. The ERRCHK "error level 2" printed for `GEN3` + `OFF QUAD` is a warning; the run continues. Remember that it leaves the limiter off (section 4.3) |
| `LIMITER [ursell] [qb]` | switches quadruplets off where the Ursell number exceeds 10; relaxes the action limiter where the breaking fraction exceeds `qb` (default 1 = never). | defaults |

### 3.3 Depth-induced breaking

Breaking is on by default: Battjes and Janssen (1978) with `alpha` 1.0
and `gamma` 0.73 (Hmax = gamma d). With `WEC_VF` + `WDISS_WAVEMOD` this
dissipation is the force that drives the set-up and the cross-reef
current, so it is the single most influential SWAN choice for reef
circulation.

| Command | What it does | Verdict |
|---|---|---|
| `BREAKING CONSTANT [alpha] [gamma]` | fixed breaker index. `gamma` 0.73 is the Battjes and Stive (1985) average over beach profiles; 0.78-0.8 the Miche limit; reef-crest observations commonly give H/d of 0.8-1.1 at the crest | **use as the baseline** (0.73, every run so far), with `CONSTANT 1.0 0.8` as the first **sensitivity**: on A15 it moves the breakpoint shoreward and raises the dissipation on the crest, hence the set-up and the jet |
| `BREAKING BKD [alpha] [gamma0] [a1] [a2] [a3]` | Salmon et al. (2015): breaker index from the local bottom slope and the mean k d, gamma = (gamma0 + a1 beta)/tanh((gamma0 + a1 beta)/(a2 + a3 k d)); switches on the directional-spread correction | **to test**: the theory fits reefs better than a flat-bottom gamma (steep forereef, abrupt depth change), and the SWAN team recommends it for shallow water. Expect larger gamma on the 1:5 forereef and smaller on the flat reef top; compare set-up and crest transport against the constant-gamma member |
| `BREAKING TG`, `VARIABLE`/`NELSON`, `RUESSINK`, `ASYM` | Thornton and Guza (1983) Rayleigh-weighted dissipation; Nelson's slope-dependent gamma for beaches; Ruessink's k d dependence; an asymmetry-based index (needs triads with biphase; undocumented) | TG is the second **sensitivity**: it breaks all waves gradually rather than the highest fraction, which spreads the dissipation over a wider forereef band. The others are beach tunings |
| `DIRECTIONALITY [spread]` | reduces dissipation for directionally spread seas. | off except through `BKD` |
| `FREQDEP` | frequency-dependent distribution of the breaking dissipation. | off |
| `OFF BREAKING` | - | never |

### 3.4 Bottom friction

| Command | What it does | Verdict |
|---|---|---|
| `FRICTION MADSEN [kn]` | Madsen et al. (1988) eddy-viscosity model with the friction factor from the Nikuradse roughness `kn`; the only law that takes the spatially varying roughness ROMS sends (`KN = max(ZO, kn)`). Source default `kn` 0.05 m | **use**, with `kn` set to the floor the roughness field needs (0.3 m today = 30 x 0.01 m; 0.05 m with a smoother bed; see section 1.5) |
| `FRICTION JONSWAP [cfjon]` | constant coefficient (0.038 m2/s3 since 41.49); ignores the ROMS roughness | keep off: no spatial roughness, and inconsistent with `SSW_BBL` |
| `FRICTION COLLINS [cfw]` | drag law with a dimensionless coefficient; would read ROMS's roughness length as a coefficient | keep off |
| `FRICTION RIPPLES [S] [D]` | Smith et al. (2011) ripple roughness from grain size | off (no sand) |

The vegetation-route runs get a near-zero bed friction automatically
(coupler floor 0.0015 m): the canopy takes the energy instead.

### 3.5 Triads

| Command | What it does | Verdict |
|---|---|---|
| `TRIAD` (bare word = `DCTA [trfac 4.4] [p 4/3] COLL`) | Booij et al. (2009) distributed collinear triads: generates all sub- and super-harmonics and the k^-4/3 shallow-water tail; active only where the Ursell number exceeds 0.1 | **on** (as now; the realistic case runs without it, a **to test** inconsistency): across a 0.5 m crest and a 1-2 m reef flat the Ursell number is well above 0.1, so energy moves from the 10 s peak into harmonics (and into infragravity bands SWAN does not carry). It changes the near-bottom orbital velocity and the bottom period that `SSW_BBL` uses, and the breaking dissipation profile. Cost: moderate (SWAN only) |
| `TRIAD LTA [trfac 1.0] [cutfr -1]` | Eldeberky's lumped approximation, extended with the p/3 interaction in 41.51; self-self interactions only | the classic choice; DCTA supersedes it in the SWAN team's recommendations |
| `TRIAD FTIM`, `TRIAD SPB` | full interaction model (costly), stochastic parametric model (not robust) | off |
| `BIPHASE ELDEBERKY [urcrit 0.63]`, `SAPRYKINA`, `DEWIT` | biphase parameterization; 0.63 (Doering and Bowen) instead of Eldeberky's 0.2, which "triggers instability" (SWAN technical manual section 2.3.4) | default |
| `TRANSFER` | interaction coefficient for shoaling waves; `QUADWAVE` is chosen automatically for DCTA | default |

Spectral resolution matters once triads are on: the harmonics of a 0.1 Hz
peak sit at 0.2 and 0.3 Hz, which the current 21 logarithmic bins over
0.04-1.0 Hz (df/f = 17.5 %) resolve coarsely. 34 bins (df/f = 10 %, the
DIA calibration value) is the matching **sensitivity** (section 4.1).

### 3.6 Vegetation in SWAN

| Command | What it does | Verdict |
|---|---|---|
| `VEGETATION 1 [height] [diamtr] [nstems] [drag]` (+ `INPGRID NPLANTS`) | Dalrymple (1984) / Mendez and Losada (2004) cylinder dissipation, height and diameter uniform, density from the plant grid (coupled from ROMS) | fine when only the density varies in space |
| `VEGETATION 3 [height] [diamtr] [nstems] [drag]` | COAWST's `SVEG_COAWST`: density, height, diameter and thickness per cell from ROMS, Cauchy-number flexibility (inert for rigid corals), KC-number drag; `[drag]` 1 = Cd 1, 2 = Mendez and Losada Cd | **use with the canopy** (decided 2026-10-22): zone-specific height or diameter needs it. Requires the engine's `swan-vegetation-fixes` (unallocated Young's modulus array, flexible formulas, the emergent Cd fixed at 1.95, plant fields read on the wrong grids, Cd output always 0). Stock v3.9 crashes or silently uses Cd 1.95 wherever plants reach the surface, which a 0.4 m canopy does on the 0.5 m crest at low tide |
| `VEGETATION 2` | Jacobsen et al. (2019) frequency-dependent canopy model, no layering, no current effects | off |
| `VEGCOAWST` | sets `IVEG = 2` although the COAWST routine answers to 3: inconsistent in the source | do not use |
| `INPGRID NPLANTS` (no `READINP`) | required in coupled runs or SWAN ignores the coupled density and uses `[nstems]` everywhere | **required** |

Consistency: Cd = 1 in both models for the test canopies, and the same
D, h, n (`VEG_SWAN_COUPLING` guarantees it); `plant_thickness = (pi/4) D`.

### 3.7 Other source terms and processes

| Command | What it does | Verdict |
|---|---|---|
| `SETUP` | wave set-up inside SWAN (SOR solver); fatal under MPI | never in coupled runs: ROMS computes the set-up from the same dissipation |
| `DIFFRACTION` | phase-decoupled refraction-diffraction; needs stationary under-relaxation to converge | keep off: it does not converge in nonstationary mode and ROMS's circulation does not see wave phase. Diffraction into the lee of reef passes is a real process the model omits; a note for the discussion section rather than a switch |
| `MUD`, `TURBULENCE`, `ICE`/`SICE`, `BRAGG`, `SCAT`, `SURFBEAT`, `OBSTACLE` | mud damping, turbulent-viscosity damping, sea ice, Bragg scattering, quasi-coherent scattering, infragravity module (stationary only), sub-grid obstacles | off. `SURFBEAT` would be the way to put infragravity energy into SWAN, but it is stationary-only and cannot run coupled; infragravity motions on the reef flat (a known driver of reef-flat currents and lagoon exchange) are therefore absent from the model, and `TRIAD` cannot replace them |
| `OFF REFRAC`, `OFF FSHIFT` | no refraction; no current-induced frequency shift | never (`FSHIFT` off would remove the Doppler shift the coupling is for) |
| `OFF BNDCHK`, `SET [hsrerr]` | silence the boundary Hs mismatch warnings | **use `OFF BNDCHK`** in nonstationary coupled runs if the warning count ever approaches `MAXMES` (200): the warnings are harmless and the stop is not |
| `OFF WINDGROWTH`, `OFF WCAP` | - | off (nothing to switch off without wind) |

### 3.8 Infragravity motions: what the model lacks, and the cheapest way in

Neither model carries infragravity (IG) motions: SWAN is phase averaged
with a lowest frequency of 0.04 Hz, and ROMS receives only the mean wave
forcing, so wave-group-forced long waves (bound long waves released at the
breakpoint, breakpoint forcing on the forereef, resonant reef-flat
oscillations) are absent. On reef flats these are a known part of the
set-up variability, the cross-reef transport and the run-up; the question
is whether they matter for the encyclopedia's metrics (tidal-cycle means
of set-up, transport and residence time) or only for extremes. Routes, in
order of effort:

| Route | What it is | Effort and limits |
|---|---|---|
| **InWave** (`INWAVE_MODEL`, COAWST's own IG model, v2.0 in this source) | a wave-group-resolving action balance for the short-wave envelope, stepped with ROMS, with `WEC_VF` forcing that varies at the group time scale, so ROMS generates the IG waves itself; forced at the boundary by a SWAN 2-D spectrum file (`INWAVE_SWAN_COUPLING`), with breaking by `WDISS_GAMMA` or `WDISS_ROELVINK`, friction `WDISS_FRIC`, Doppler shift `DOPPLER`; v3.9 added curvilinear metrics; examples `Inwave_shoreface`, `Inlet_test/InWave`, `Delilah`, `DuckNC` | the only built-in route, so "not too much work" in principle: a new case folder, `ND` directional bins in `ocean.in` (11 are already declared), a boundary spectrum from a standalone SWAN run. It replaces SWAN: `INWAVE_SWAN_COUPLING` means reading a SWAN 2-D spectrum file (`.spc2d`, from a separate standalone SWAN run) at the boundary, not running SWAN alongside (`Projects/Inlet_test/InWave/inlet_test.h` has no `SWAN_MODEL` or `MCT_LIB`; `globaldefs.h` forces `BULK_STOKES` with `INWAVE_MODEL`, so the spectral Stokes drift is lost too), so SWAN's refraction with currents, triads, whitecapping, vegetation dissipation and two-way current feedback are gone or approximated by InWave's own `DOPPLER` and dissipation options; periodic boundaries, the closed O-grid, the restart fixes and the canopy have never been run with it; cost is roughly `ND` extra 3-D advected fields every ROMS step. The test is one A15 member against the SWAN-coupled baseline: does the tidal-mean set-up and transport change, and by how much |
| SWAN `SURFBEAT` (Reniers and Zijlema 2022) | SWAN's IG module | stationary only, two-`COMPUTE` workflow, regular grids: cannot run coupled. Useful offline, as a standalone stationary A15 run, to estimate the IG energy reaching the reef flat for a given sea state and decide whether the question is worth the InWave effort |
| IG at the open boundary of ROMS | a free long wave imposed through `ANA_FSOBC`/`ANA_M2OBC` at the group period (25-250 s) | cheap but physically weak: on a reef most IG energy is generated at the breakpoint, not incident; it only tests the reef flat's resonant response |
| phase-resolving models (SWASH, XBeach surfbeat, FUNWAVE) | the standard tools for reef IG | not coupled to ROMS; a separate study, not an option of this system |

Recommendation: no run now. Note it as a known omission in the methods;
when the encyclopedia's set-up and transport results are in, run the
standalone `SURFBEAT` estimate on A15, and if IG energy on the reef flat
is a significant fraction of the sea-swell energy, try InWave on A15
(one member, one day) before deciding anything about Moorea.

## 4. SWAN numerics (`swan.in`)

### 4.1 Grids and spectral resolution

| Item | Current | Verdict |
|---|---|---|
| `MODE NONSTATIONARY TWODIMENSIONAL` | both | required for coupling (1-D is fatal under MPI) |
| `COORDINATES CARTESIAN REPEATING` | yes | periodic in x; curvilinear periodic grids and the closed O-grid are engine additions |
| `CGRID CURVILINEAR ... EXC` | the ROMS grid | same grid as ROMS (decided) |
| `CIRCLE [mdc]` | 72 (5 deg) | 5 deg is the better resolution for refraction over a steep forereef and for the garden-sprinkler-free BSBT scheme; 36 (10 deg) is a cost choice on large grids (SWAN time scales with `mdc`), and the **sensitivity** there is 72 once the process split is rebalanced |
| `[flow] [fhigh] [msc]` | 0.04-1.0 Hz, 20 (21 bins, df/f 17.5 %) | 0.04 Hz keeps the first bin empty (the manual's rule); 1.0 Hz covers the third harmonic of a 10 s swell and short wind sea; **sensitivity: msc 34** (df/f 10 %) when triads are on. Below 0.04 Hz nothing is carried: no infragravity band |
| `SET DEPMIN` | 0.10 | depths below `DEPMIN` are clipped to it, not dried; keep it at or below ROMS's `DCRIT` (0.10) so SWAN never sees a wetter bed than ROMS |
| `SET INRHOG 1 NAUTICAL` | yes | required (dissipation in W/m2 for ROMS; nautical directions for the TPAR files) |
| `SET [froudmax]` | default 0.8 | caps the current SWAN receives at 0.8 sqrt(g d): on a 0.3 m crest that is 1.4 m/s, below the crest-jet speeds a shallow reef produces (1.2-2.4 m/s in the realistic case), so SWAN sees a clipped current there. Harmless for the waves (the crest is a dissipation zone) but worth knowing when comparing SWAN's current field with ROMS's |
| `SET [pwtail]` | default 4 | the f^-4 high-frequency tail (5 with Janssen); untouched |
| `INPGRID CURRENT/WLEV/FRIC ... NONSTAT`, no `READINP` | yes | required in coupled runs (section 5.3) |
| `INPGRID BOTTOM` + `READINP BOTTOM` | yes | SWAN's own copy of the bathymetry; must equal the ROMS grid's `h` (the generators write both) |
| `NSGRIDS 1` | yes | one wave grid |

### 4.2 Propagation scheme

| Command | Scheme | Verdict |
|---|---|---|
| `PROP BSBT` | first-order upwind, implicit, unconditionally stable, diffusive; the only scheme fully implemented on curvilinear grids | **use** (every COAWST example). The technical manual's own assessment (section 3.2.2): nearshore solutions are set by the source terms and are "on the whole rather insensitive" to the geographic propagation scheme; the higher-order schemes matter for swell over thousands of kilometres |
| default nonstationary = S&L (Stelling and Leendertse), `GSE [waveage]` | second order in space and time, three time levels; "not fully implemented" for curvilinear grids per ERRCHK; the garden-sprinkler counter-diffusion only works with it and is conditionally stable | keep off: the crest is a few cells wide, where S&L's lower diffusion is not an advantage and its curvilinear warning is a risk |
| `SORDUP` | second-order upwind; stationary only | not applicable |
| `FLUXLIM` | flux-limited theta scheme (undocumented) | off |

### 4.3 Time step, iterations and limiters

SWAN's time stepping is fully implicit (four-sweep Gauss-Seidel), so
`deltc` has no stability limit; it sets the accuracy of the source-term
splitting and how far the solution lags the forcing.

| Item | Current | Verdict |
|---|---|---|
| `COMPUTE NONSTATIONARY ... [deltc]` | 120 s | it divides the 600 s coupling interval. The wave field crosses A15's 1 km forereef in about 100 s at cg 10 m/s, so 120 s is one crossing per step: **sensitivity: 60 s on A15** (cheap, SWAN is 30 % of that run). on a 10 m grid 60 s is already finer than the crossing time of the crest |
| `NUM NONSTAT [mxitns]` | default 1 | one sweep set per time step; the solution lags the forcing by up to a step. **Sensitivity: 2** together with the 60 s test: if neither changes the crest Hs by more than a few percent, the current settings are converged |
| `[limiter]` | default 0.1, but **disabled by `OFF QUAD`** (`PNUMS(20) = 1e20`) | the breaking source is Newton-linearized and implicit, so the runs are stable without it; if a run ever needs the limiter back, give `NUM STOPC ... NONSTAT 1 0.1` explicitly. Note that with the limiter on, Hs across the breaker zone becomes limiter dependent (technical manual section 3.7); off is the cleaner state for a surf-zone model |
| `NUM STOPC [dabs] [drel] [curvat] [npnts]` | defaults 0.005 m, 0.01, 0.005, 99.5 % | only meaningful with `mxitns > 1` |
| `NUM DIRIMPL [cdd]` | default 0.5 (half central, half upwind in direction) | ERRCHK recommends `cdd = 1` (full upwind) where currents are present; 0.5 is more accurate but can produce spurious directional oscillations near strong depth or current gradients. **To test: `NUM DIRIMPL 1`** on grids with strong currents and steep forereefs (reef passes with 1-2 m/s jets); on A15 keep 0.5 unless noise appears in `dir` near the crest |
| `NUM SIGIMPL [css]` | default 0.5, implicit SIP solver | same reasoning for the frequency shift: `css = 1` **to test** with strong pass currents |
| `NUM CTHETA [cfl]` | off unless given (0.9 when given) | limits the refraction turning rate per step: the technical manual (section 3.8) describes exactly our situation, refraction on coarse bathymetry gradients in nonstationary runs producing spurious directional turning. **Tested on A15 2026-11-03**: `NUM CTHETA 0.9` within 0.7 % of the default, `CSIGMA 0.9` never acts, `DIRIMPL 1` within 1 %: no limiter needed on A15 (untested at a pass with strong currents); cost nil |
| `NUM CSIGMA [cfl]` | off unless given | the same limiter for the frequency shift on strong current gradients; pair it with `CTHETA` in that test |
| `NUM STAT [mxitst] [alfa]` | 50, 0 | stationary only; `alfa` is zeroed by `MODE NONSTAT` |
| `RESTART 'output/swan_rst.dat' FREE 1 HR` | yes | the engine's `swan-exact-restart` makes it exact; keep |
| `HOTFILE`, `INIT HOTSTART` | hot-start files | the restart mechanism uses them; `INIT DEFAULT` (JONSWAP from local wind = zero without wind) is what `MODE NONSTAT` sets for a cold start, and the Hs ramp in the TPAR files does the spin-up |
| `BOUNDPAR`/`BOUNDSPEC ... JONSWAP 3.3 PEAK DSPR DEGREES` | yes | JONSWAP shape, peak period, directional spread in degrees (A15: 4 deg, narrow; 30 deg is the realistic choice); the spread sets how much energy refracts into the lee and is a physics choice for the ensembles |
| `OFF BNDCHK` | not set | see section 3.7 |

### 4.4 Output

`BLOCK 'COMPGRID' NOHEADER 'output/*.nc' LAY 4 ...` for every quantity the
analysis needs (the engine's `swan-netcdf-output` makes all 2-D quantities
available as 32-bit floats, compressed). The budget terms (`DISSIP`,
`DISBOT`, `DISSURF`, `DISVEG`, `PROPAGAT`, `REDTRIAD`...) that A15 writes
are the right diagnostics for the wave energy budget across the reef;
`SPECOUT` at a few points (forereef, crest, lagoon) at hourly intervals is
cheap and shows the harmonic generation that the integrated parameters
hide. `SWAN_SINGLESPEC` must stay off for `SPECOUT` to work with several
SWAN processes.

## 5. Coupling (`coupling.in`, coupler cpp options)

### 5.1 What is exchanged

Every `TI_OCN2WAV` / `TI_WAV2OCN` seconds (the two must be equal in
practice) the MCT coupler moves, on the same grid without interpolation:

| Direction | Fields | Used by |
|---|---|---|
| SWAN to ROMS | breaking, bottom-friction and whitecapping dissipation (`DISSURF`, `DISBOT`, `DISWCAP`, in W/m2 with `INRHOG 1`; ROMS divides by `rho0`), Hs, peak and bottom periods, mean and peak directions, mean and peak wavelengths, orbital velocity `UBOT` (rms), breaking fraction `QB`, directional spread, peakedness; with the canopy: vegetation dissipation and drag coefficient; with `SPECTRUM_STOKES`: per-frequency Stokes partials | `WEC_VF` forcing, `SSW_BBL`, GLS surface terms (`TKE_WAVEDISS`, `ZOS_HSIG`), the Stokes drift profile |
| ROMS to SWAN | sea level, the `UV_KIRBY`-weighted current (one field per frequency bin with `UV_BANIHASHEMI`), bottom roughness `ZO` = 30 z0_Nikuradse (floored at 0.05 m, 0.0015 m with `VEG_SWAN_COUPLING`), plant density, height, diameter and thickness with `VEG_SWAN_COUPLING`; bathymetry only with `SED_MORPH` | depth and current refraction, Doppler shift, `FRICTION MADSEN`, `VEGETATION 3` |

Between exchanges each model holds the other's fields constant: SWAN sees
a water level and current that change in steps of `TI_OCN2WAV`; ROMS
recomputes the Stokes drift and the breaking force from the same wave
fields every step while its own depth and sea level evolve.

### 5.2 Options

| Option | What it does | Verdict |
|---|---|---|
| `MCT_LIB` | couple through MCT (the internal `ROMS_COUPLING`, `SWAN_COUPLING`, `WAVES_OCEAN` follow). | on |
| `MCT_INTERP_OC2WV` (+ SCRIP weights) | interpolation between different ocean and wave grids. | off: SWAN runs on the ROMS grid (decided 2026-10-20). A15 originally had a separate SWAN grid; the port made them the same. Interpolation across the periodic seam is untested, and the same grid removes one source of mismatch between the breaking force and the depth it was computed on |
| `NnodesOCN`, `NnodesWAV` | processes per model; their sum is the MPI size. | A15 10 + 6 on 16 vCPUs (benchmarks in `case_design.md`, 2026-10-21): the split where ROMS stops waiting for SWAN once SWAN is built at `-O3` |
| `TI_OCN2WAV`, `TI_WAV2OCN` | exchange intervals; must be integer multiples of SWAN's `deltc`. | 600 s (every run so far). **Sensitivity: 300 s.** The argument for shorter: on a 0.5 m crest a 0.15 m tide changes the breaking depth by 30 % over a tidal cycle, and ROMS's wave forcing is frozen for 600 s at a time (the tide moves 13 mm in 600 s, which is small); the wave set-up and the crest jet respond within minutes to the wave forcing, but the forcing itself only changes with the tide, so 600 s should be adequate. The cost of 300 s is one more MCT exchange and SWAN output computation per 300 s, a few percent. Worth one A15 member to confirm the response is insensitive |
| `UV_KIRBY` / `UV_BANIHASHEMI` / `UV_CONST` / none | which current SWAN receives (section 1.8). | `UV_KIRBY`; `UV_BANIHASHEMI` tested 2026-11-03: within 0.5 % |
| `ZETA_CONST` | SWAN gets no sea level. | off |
| `VEG_SWAN_COUPLING` | plant fields to SWAN (section 1.7). | on with the canopy |
| `SWAN_SINGLESPEC` | one spectral output file per run instead of per process; breaks `SPECOUT` with several SWAN processes. | off (the engine removes it from every header) |
| `SWAN_NS_PERIODIC` | COAWST-only north-south periodic exchange. | off (we are periodic in x through `REPEATING`) |
| `WAVE_PARTITION` | export two spectral partitions. | off |
| `SCRIP_COAWST_NAME` | weights file; made automatically at start-up if missing. | unused on the same grid |
| `NESTING` in SWAN (`NSGRIDS`) | child wave grids. | off |

### 5.3 Consistency rules for coupled runs

1. `swan.in` must carry `INPGRID CURRENT`, `WLEV` and `FRIC` lines with
   `NONSTAT` and no `READINP`: the COAWST build compiles the file reading
   out and fills these arrays from MCT, but without the `INPGRID` lines
   the sea level is never added to the depth, the Froude limiter is
   skipped, and the ROMS roughness is never used (`swanmain.ftn` lines
   9071-9176; SWAN catalogue section 3). With the canopy, also
   `INPGRID NPLANTS` (no `READINP`).
2. `SET ... INRHOG 1` so that the dissipation arrives in W/m2.
3. SWAN's `deltc` divides `TI_OCN2WAV`; ROMS's `DT` divides it too.
4. The roughness SWAN uses with `FRICTION MADSEN [kn]` is
   `max(ZO from ROMS, kn)`: the `kn` in `swan.in` is a floor, not a
   placeholder. Set it to the smallest roughness the ROMS field can take
   (0.05 m is the coupler's own floor without the canopy).
5. Periodic SWAN (`COORDINATES ... REPEATING`) needs the engine's
   `swan-periodic-fixes` and `swan-periodic-curvilinear`; the closed
   O-grid needs `swan-closed-ring`. Non-periodic SWAN under periodic ROMS
   gave a 58 mm/s jump in the alongshore current at the seam and up to
   0.3 m of crest Hs error near the sides (`case_design.md`).
6. Restarts: `RESTART 'output/swan_rst.dat' FREE 1 HR` in `swan.in` and
   `PERFECT_RESTART` in ROMS; with the engine's restart fixes both models
   restart exactly, which is what the Spot segments rely on.
7. ROMS tilings `1 x N` and any SWAN y-strip count give bit-identical
   results; `NtileI > 1` differs at rounding level.

## 6. Compiler and build options

What COAWST does as shipped (`build_coawst.sh`, `Compilers/Linux-gfortran.mk`,
`SWAN/src/CMakeLists.txt`), what the engine changes (`build/coawst/Dockerfile`,
documented in `build/coawst/patches/2-improvements/build-settings.md`), and
what else is available.

### 6.1 Build-script switches (`build_coawst.sh`)

| Switch | Meaning | Verdict |
|---|---|---|
| `USE_MPI`, `USE_MPIF90` | distributed memory, `mpif90` wrapper. | on: coupled runs need MPI |
| `USE_OpenMP` | shared-memory threads. | off: cannot be combined with MPI in ROMS, and SWAN's MPI build is what the coupler needs |
| `USE_NETCDF4` | NetCDF-4 library via `nf-config`. | on (required for SCRIP and for `OUT_NETCDF4`) |
| `USE_LARGE` | 64-bit addressing flag (no effect in the gfortran makefile). | on, harmless |
| `USE_DEBUG` | `-g -O0 -fbounds-check -fbacktrace -fcheck=all -fsanitize=address,undefined -finit-real=nan -ffpe-trap=invalid,zero,overflow` instead of `-O3 -ffast-math`. | off for production; a debug build is the tool for a blow-up whose location the `NINFO = 1` records do not explain (10-30x slower) |
| `USE_PARALLEL_IO`, `USE_PIO`, `USE_PNETCDF`, `USE_HDF5` | parallel I/O libraries. | off |
| `which_MPI`, `FORT` | `openmpi`, `gfortran` in the image. | - |
| `NJOBS` (`-j`) | parallel make. | 4-8 |

### 6.2 ROMS compiler flags (gfortran)

| Flag | Stock | Engine | Why |
|---|---|---|---|
| `-O3` | yes | yes | loop vectorization, inlining; safe for ROMS; the expected gain over `-O2` is small for memory-bound stencils but it is the configuration every ROMS build uses |
| `-ffast-math` | yes | **no** | lets the compiler reorder sums, replace divisions, assume no NaN and flush denormals: results then depend on compiler decisions, the NaN blow-up check could be optimized away, and tiny values become zero. Measured on A15: no speed difference within the 8 % run-to-run spread (`build-settings.md`). Keep it off: reproducibility across machines is what the ensembles and the bit-identical restart tests rely on |
| `-march=x86-64-v3` | no (generic) | yes | AVX2 and FMA: every current x86 cloud machine (c2d, c3d, n2) has them; FMA changes the last bits (one rounding instead of two). `-march=native` is avoided so the image does not depend on the build machine. `x86-64-v4` (AVX-512) exists on c3/c3d/n2 but not on c2d (Zen 3), and would not help a memory-bound code; stay at v3 |
| `-g` | no | yes | line numbers in backtraces; no code change |
| `-frepack-arrays`, `-fallow-argument-mismatch` | yes | yes | ROMS defaults; the second is required by gfortran 10 and later for ROMS's MPI calls |
| `-ffree-line-length-none`, `-ffixed-form` per file | yes | yes | source form |
| `ROMS_FFLAGS_EXTRA` (engine build arg) | - | empty | e.g. `-fcheck=bounds` for a checking build without the full debug set |
| `-fopenmp` | with `USE_OpenMP` | no | - |
| ifort / ifx (`Linux-ifort.mk`, `Linux-ifx.mk`) | `-ip -O3 -xHost` style | not used | Living with ROMS section 23: with ifort use `-xHost -no-heap-arrays` and `ulimit -s unlimited` (ROMS's automatic arrays on the stack, about 8 % faster than heap). The image is gfortran-only; an Intel build is not worth a second toolchain for a 10-20 % gain on a code whose cost is dominated by SWAN and the WEC kernel |

### 6.3 SWAN compiler flags (CMake)

| Flag | Stock | Engine | Why |
|---|---|---|---|
| `-O` (= `-O1`) | yes | **`-O3`** | SWAN is the slow side of a coupled run; at `-O3` it keeps up with ROMS and ROMS's waiting time drops by three quarters: the coupled A15 run is 1.7x faster (267 s to 152 s per simulated hour on AMD; 315 to 198 on Intel), results within 6e-5 relative after 1 h (`build-settings.md`) |
| `-march=x86-64-v3 -g` | no | yes | as for ROMS |
| `-w -fno-second-underscore -ffree-line-length-none -fallow-argument-mismatch` | yes | yes | SWAN's own |
| `SWAN_FFLAGS_EXTRA` | - | empty | `-fcheck=bounds` found the SWAN output and halo bugs |
| switches `-unix -impi -mpi -netcdf` | yes | yes | SWAN's preprocessor switches: MPI build with NetCDF output; `-netcdf` is what the engine's NetCDF output patches extend |
| `-jac`, `-metis` | no | no | Jacobi/METIS parallel variants for unstructured grids |

### 6.4 MCT

Built once at `-O2 -fallow-argument-mismatch`; it only moves data, so
optimization level is irrelevant.

### 6.5 Output format and other build-time switches of the engine

| Build argument | Default | Meaning |
|---|---|---|
| `BUILD_SETTINGS` (`engine` or `stock`) | engine | the flags above and `SWAN_SINGLESPEC` removal; `stock` with `SERIES=none` gives COAWST exactly as shipped, for comparisons |
| `OUTPUT_OPTIONS` | `+OUT_NETCDF4 +DEFLATE` | compressed NetCDF-4 (lossless, 2-4x smaller, 1-2 % run time); `""` for classic files |
| `CPP_OPTIONS="+X -Y"` | empty | extra defines without a new case folder, e.g. `+STEP2D_FB_AB3_AM4`, `+BSTRESS_IMPLICIT -SPLINES_VVISC`, `+VEG_DRAG_IMPLICIT`, `+TKE_WAVEDISS +ZOS_HSIG` |
| `ARCH_FLAGS` | `-march=x86-64-v3 -g` | change for an old CPU (`-march=x86-64`) |
| `SERIES` | `series` | the patch series; `none` for stock |
| `COAWST_REF` | `26e6fb7` | the COAWST commit |

### 6.6 Run-time environment

- `OMPI_ALLOW_RUN_AS_ROOT`, `OMPI_MCA_btl_vader_single_copy_mechanism=none`
  in the image (containers run as root; the vader setting avoids a ptrace
  error for shared-memory copies).
- `ulimit -s unlimited` is only needed for the ifort stack-array build;
  gfortran with `-frepack-arrays` and heap allocation does not need it.
- `mpirun --use-hwthread-cpus --bind-to none -np (NnodesOCN + NnodesWAV)`.

### 6.7 Reproducibility

With the engine flags the same image gives bit-identical results run after
run and across Intel and AMD machines, for a fixed process split and
tiling (`build-settings.md`; `case_design.md`). Changing the tiling in i,
the number of SWAN processes or the compiler flags changes the last digits;
a scientific comparison between members must therefore use the same
image, split and tiling, which the ensemble spec enforces.

## 7. The recommended configurations in full, and what to test first

### 7.1 Idealized reef (`REEF_IDEAL_A15` and variants)

Header (`reef_ideal_a15.h`), grouped; "as now" means unchanged from the
current case files, "change" marks a recommended edit.

```
/* models and coupling */
#define ROMS_MODEL  SWAN_MODEL  MCT_LIB          (as now; MCT_INTERP_OC2WV off)
#define SALINITY  PERFECT_RESTART  SOLVE3D  MASKING  VISC_GRID
#undef  WET_DRY  CURVGRID                        (as now)
/* momentum and tracers */
#define UV_ADV  UV_COR  UV_VIS2  MIX_S_UV  DJ_GRADPS   (as now)
#define SPLINES_VDIFF                            (as now)
#undef  SPLINES_VVISC                            change: off in new builds (section 1.6)
#define TS_FIXED                                 base case only; off in _strat/_therm
/* waves */
#define WEC_VF  WDISS_WAVEMOD  UV_KIRBY          (as now; SPECTRUM_STOKES is automatic)
#define BOTTOM_STREAMING                         (since 2026-11-03)
#undef  SURFACE_STREAMING  WAVE_MIXING  DISSIP_BREAK_DIR
/* bottom */
#define SSW_BBL  SSW_CALC_ZNOT  SSW_LOGINT  SSW_LOGINT_WBL   (as now)
/* LIMIT_BSTRESS off as now; +BSTRESS_IMPLICIT -SPLINES_VVISC for crest-jet members */
/* canopy (_veg cases) */
#define VEGETATION  VEG_DRAG  VEG_TURB  VEG_SWAN_COUPLING    (as now)
#define VEG_STREAMING                            (since 2026-11-03)
#undef  VEG_FLEX
/* +VEG_DRAG_IMPLICIT for patchy or dense canopies (build arg) */
/* turbulence */
#define GLS_MIXING  RI_SPLINES  KANTHA_CLAYSON  N2S2_HORAVG  (off with VEG_TURB; as now)
/* candidates, section 1.6:  TKE_WAVEDISS  ZOS_HSIG  (to test, together) */
/* forcing and boundaries */
#define ANA_SMFLUX  ANA_FSOBC  ANA_M2OBC  ANA_*FLUX   (as now)
#define SOLAR_SOURCE                             _therm (as now)
#define TS_DIF2  MIX_GEO_TS                      _strat/_therm (as now; TNU2 = 0)
/* output */
#define AVERAGES  DIAGNOSTICS_UV                 (diagnostics only where a budget is wanted)
#define OUT_NETCDF4  DEFLATE                     (build default)
```

`ocean.in`: `N` 15 (since 2026-11-03; was 10), `Vtransform` 2, `Vstretching` 4, `THETA_S` 3,
`THETA_B` 2, `TCLINE` 20; `DT` 6, `NDTFAST` 24 (3 and 12 with patchy
explicit canopies or N^2 >= 3e-4); `Hadvection`/`Vadvection` `MPDATA`;
LBC: `Per Clo Per Che` (zeta), `Per Clo Per Shc` (ubar, vbar),
`Per Clo Per Gra` (u, v, T, S) in the base case and `RadNud` in `_strat`
and `_therm`, `Per Clo Per Gra` (TKE), and `Per Clo Per Gra` (change from
`Gra Clo Gra Gra`) for the Stokes and wave-action variables; `VISC2`
0 (user, 2026-11-02; 0.001 in every run before that date), `TNU2` 0; `AKV_BAK` 5e-5, `AKT_BAK` 5e-6; GLS k-epsilon constants
as now; `GLS_Kmin` 1e-8 (A15 default since 2026-11-03, was 7.6e-6); `Zob` 0.01 (inert with `SSW_CALC_ZNOT`:
the roughness is `grain_diameter` 0.12 m in the initial file), `Zos`
0.5 (inert unless `ZOS_HSIG` or `CHARNOK`; with `ZOS_HSIG` set
`ZOS_HSIG_ALPHA` 0.5), `SZ_ALPHA` 0.25 for `TKE_WAVEDISS`, `WEC_ALPHA` 0;
`TCOEF` 3.2e-4 (change from 1.7e-4 in `_strat`, already so in `_therm`),
`SCOEF` 7.6e-4, `R0` 1027; `OBCFAC` 10 and the nudging band switches on in
`_strat`/`_therm` (`Lm3CLM`, `LtracerCLM`, `LnudgeM3CLM`, `LnudgeTCLM`),
`TNUDG`/`M3NUDG` 1 day; `LuvSponge`/`LtracerSponge` F; `NINFO` 1;
`LcycleRST` T for production.

`swan.in`: `MODE NONSTATIONARY TWODIMENSIONAL`; `SET DEPMIN 0.10 INRHOG 1
NAUTICAL`; `COORDINATES CARTESIAN REPEATING`; `CGRID CURVILINEAR 202 110
... CIRCLE 72 0.04 1.0 20`; `INPGRID CURRENT/WLEV/FRIC ... NONSTAT`, and
`INPGRID NPLANTS` in the canopy cases; `GEN3`; `FRICTION MADSEN 0.3`
(lower the 0.3 to the smallest intended KN when the roughness field has
smooth patches); `OFF QUAD`; `BREAKING BKD 1.0 0.54 7.59 -8.06 8.09` (since 2026-11-03; was `CON 1.0 0.73`); `TRIAD`; `PROP BSBT`;
`VEGETATION 3 0.4 0.5 1 1` with the canopy; `COMPUTE NONSTATIONARY ...
120 SEC`; `RESTART ... FREE 1 HR`; add `OFF BNDCHK` if boundary warnings
ever accumulate.

`coupling.in`: 10 ROMS (1 x 10) + 6 SWAN on c2d-standard-16, 600 s both
ways.

Build: engine defaults; `CPP_OPTIONS` as the member needs
(`+VEG_DRAG_IMPLICIT`, `+BSTRESS_IMPLICIT -SPLINES_VVISC`,
`+TKE_WAVEDISS +ZOS_HSIG`, `+STEP2D_FB_AB3_AM4`).

### 7.2 What to test first, and why in this order

Each test is one or two short members against the current configuration
on A15 (the project's rule is to test numerics on the idealized reef, which
is 5-15x cheaper per simulated hour than a realistic grid). Costs use the
measured rate of about $0.08 per simulated day on Spot machines.

| # | Test | Members (vs current) | Why first | Decides |
|---|---|---|---|---|
| 1 | Breaking parameterization | `BREAKING CON 1.0 0.8`; `BREAKING BKD` (defaults); `BREAKING TG` (A15, 24 h each) | the breaking dissipation is the force that drives the whole reef circulation; everything downstream (set-up, jet, flushing, heat, larvae) scales with it; no run has ever varied it | whether the encyclopedia needs a breaking-parameter axis, and which formulation is the baseline |
| 2 | Surface turbulence from breaking | `+TKE_WAVEDISS +ZOS_HSIG` (A15 base and `_strat`, 24 h) | today the breaking force acts on an unmixed surface layer; this changes the vertical structure of the cross-reef flow, which the particle tracking samples | whether it becomes the default (expected yes) |
| 3 | SWAN time step and iterations | `deltc` 60 s; `NUM NONSTAT 2` (A15, 24 h) | cheap; the closed-ring test showed 1 vs 5 iterations move crest Hs by 8 cm, 3.5x more than the seam itself | whether 120 s / 1 iteration is converged |
| 4 | Triads on and off | the `TRIAD` line removed (A15, 24 h) | harmonics change the bottom period and orbital velocity that the BBL uses; the realistic case runs without triads, A15 with them | whether the two set-ups are comparable, and whether triads matter on the reef flat |
| 5 | SWAN numerics with currents | `NUM DIRIMPL 1 SIGIMPL 1 CTHETA 0.9 CSIGMA 0.9` (A15, 24 h; then any grid with strong pass jets) | ERRCHK's own recommendation with currents; the A15 pass carries up to 0.9 m/s against the swell | whether the directional field near the pass is noisy today |
| 6 | Coupling interval | 300 s (A15, 24 h) | the only coupling parameter never varied | closes the question |
| 7 | Barotropic kernel on A15 | `+STEP2D_FB_AB3_AM4` (A15, 24 h) | the engine test says equal accuracy; a 5-15 % saving over 100 week-long members | whether A15 switches (all members at once) |
| 8 | Nonlinear equation of state | `+NONLIN_EOS` rest test, then 24 h thermal (A15 `_therm`; then any case with river water) | the thermal expansion of 28-36 C water is not linear; the pressure-gradient cost must be measured at rest first | linear or nonlinear EOS for the thermal and river cases |
| 9 | Canopy turbulence at rest | `_veg_strat` at rest with `VEG_TURB` off (A15, 24 h) | the unexplained 1e-3 m2/s backreef diffusivity sets how fast the reef flat destratifies | whether the canopy source or GLS in shallow water is responsible |
| 10 | Stability functions and `GLS_Kmin` | `CANUTO_A`; `GLS_Kmin` 1e-8 (A15 `_strat`, 24 h) | low priority: differences between closures are usually below those from resolution | sensitivity numbers for the methods section |
| 11 | Spectral resolution | `msc` 34 on A15 with `TRIAD` (and `CIRCLE 72` on any grid still at 36) | cost 1.5-2x on SWAN; only after 3 and 4 | whether the wave field over the forereef is resolution dependent |
| 12 | Rollers | `ROLLER_RENIERS` with `WEC_ALPHA` 0.5 (A15, 24 h, after a restart check) | shifts the breaking momentum onto the reef flat; untested restart fields | a sensitivity number, not a default |
| 13 | Current sent to SWAN | `+UV_BANIHASHEMI` (A15, 24 h) | sheared undertow under the crest jet | done 2026-11-03: within 0.5 %, keep `UV_KIRBY` |

Not worth testing (the reasoning is in the sections): `UV_U3ADV_SPLIT`
(blew up), `OMEGA_IMPLICIT` (hides blow-ups), `PJ_GRADP*` (lost the rest
test), `HSIMT` and `U3` tracers (mix more or overshoot), `LMD_MIXING`,
`UV_SADVECTION`, `WEC_BREAK_UNIFORM` as anything but a sensitivity,
`DISSIP_BREAK_DIR` with SWAN (unfilled arrays), `SETUP` and `DIFFRACTION`
in SWAN (and `SURFBEAT`, stationary only), `FRICTION JONSWAP`/`COLLINS` with coupled roughness,
`BSTRESS_IMPLICIT` on a grid with a crest under 0.4 m or rx0 above 0.2,
`WET_DRY` while nothing dries, 20 vertical levels without a new
crest-smoothing rule.

### 7.3 Pitfalls found while reading the sources

- `DISSIP_BREAK_DIR` compiles with SWAN but its x/y dissipation arrays
  are only filled by the WW3 coupler.
- `OFF QUAD` silently disables SWAN's action limiter.
- `FRICTION MADSEN [kn]` is a floor under the ROMS roughness, not a value
  that the coupling overrides.
- With `SSW_CALC_ZNOT` the roughness is `grain_diameter / 12`, and `Zob`
  in `ocean.in` does nothing.
- `INPGRID CURRENT/WLEV/FRIC ... NONSTAT` lines without `READINP` are
  what make the coupled fields act in SWAN.
- `SET INRHOG 1` or the dissipation reaches ROMS in the wrong units.
- `SWAN_SINGLESPEC` breaks `SPECOUT` with more than one SWAN process.
- `VEGCOAWST` is wired to the wrong `IVEG`; use `VEGETATION 3`.
- `PJ_GRADP` does not compile with `WET_DRY` in stock v3.9.
- `WEC_MELLOR` no longer exists; the `#undef` in the headers is a relic.
- `BSTRESS_IMPLICIT` and `VEG_DRAG_IMPLICIT` need `SPLINES_VVISC` off to
  act inside the tridiagonal solve.
- `DSTART` must equal the initial date or the step counter can overflow
  on restarts at DT 2 s.
- `NDTFAST` below about 10 (DT 1 s / NDTFAST 4 on A15) breaks the
  barotropic averaging.

## 8. Sources

Primary (the code at the pinned commit):

- COAWST `26e6fb73c5a8c4d37a83bd8339ae25c8db0ba2be` (DOI-USGS/COAWST, 2 October
  2026): `ROMS/Include/cppdefs.h`, `ROMS/Include/globaldefs.h`,
  `ROMS/Nonlinear/*.F` (`gls_corstep.F`, `BBL/ssw_bbl.h`, `WEC/*.F`,
  `Vegetation/*.F`, `prsgrd*.h`, `step2d*.h`), `ROMS/Utility/ini_hmixcoef.F`,
  `metrics.F`, `get_grid.F`, `Master/mct_roms_swan.h`, `SWAN/src/swanpre1.ftn`,
  `swanmain.ftn`, `swancom*.ftn`, `waves_coupler.ftn`, `Compilers/Linux-gfortran.mk`,
  `SWAN/src/CMakeLists.txt`, `build_coawst.sh`; the `ocean.in` and
  `vegetation.in` glossaries of the cases.
- This repository: `build/coawst/Dockerfile`, `build/coawst/patches/*/*.md`
  (status cards and tests of the 26 patches), `tests/cases/*`.
- The project's private run records: the case design document, the
  numerical-schemes notes, the case READMEs and the dated lab notebook
  (entries of 2026-10-20 to 2026-11-02), cited by date above.

Manuals (listed in `docs/manuals/README.md`, not included): COAWST User Manual v3.9 (September 2026); SWAN
user and technical manuals 41.51 (March 2026); "Living with ROMS"
(Cherian, 2020). Their versions and caveats are in that README.

Companion files in `docs/options/`:

- `swan_command_catalogue.md`: every SWAN command as the bundled parser
  reads it, with source line references, defaults and the discrepancies
  with the 41.51 manual.
- An evidence catalogue of every recorded test result, decision and open
  item, with file and line references, is kept with the private records.

Papers referred to: Shchepetkin and McWilliams (2003, 2005, 2009);
Shchepetkin (2003); Marchesiello et al. (2001, 2009); Warner et al. (2005,
2008); Umlauf and Burchard (2003); Kantha and Clayson (1994); Canuto et al.
(2001); Uchiyama et al. (2010); Kumar et al. (2012); Kirby and Chen (1989);
Banihashemi et al. (2017); Liu et al. (2021); Beudin et al. (2017); Kalra
et al. (2017); Uittenbogaard (2003); Luhar and Nepf (2016); Madsen et al.
(1988); Battjes and Janssen (1978); Battjes and Stive (1985); Thornton and
Guza (1983); Salmon et al. (2015); Eldeberky (1996); Booij et al. (2009);
Van der Westhuysen (2007, 2012); Feddersen and Trowbridge (2005); Ilicak et
al. (2012); Wu and Zhu (2010); Scully et al. (2011); Jackett and McDougall
(1995).
