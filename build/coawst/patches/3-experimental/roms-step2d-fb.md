# roms-step2d-fb.patch: ROMS's AB3-AM4 barotropic kernel, made usable in COAWST

| | |
|---|---|
| **Type** | experimental (cpp option `STEP2D_FB_AB3_AM4`) |
| **Changes results?** | with the option: a different barotropic time-stepping scheme, faster; results differ from LF-AM3 by the schemes' discretization difference. Without it: the build is unchanged |
| **Default** | off |
| **Files** | `ROMS/Nonlinear/step2d.F`, `step2d_FB.h` (rewritten), `step3d_uv.F`, `wetdry.F`; `ROMS/Modules/mod_ocean.F` |
| **Evidence** | Reef_Ideal_A15 and Circle_Island, 1 h: as close as LF-AM3 to a reference with 4x smaller time steps; ROMS's 2-D kernel 2.4-2.6x less CPU time, 2-D halo exchanges 1.4-1.7x less; options off: same preprocessed Fortran (except two line numbers) |
| **Test** | [`tests/experimental/roms-step2d-fb/run.sh`](../../../../tests/experimental/roms-step2d-fb/run.sh) ([README](../../../../tests/experimental/roms-step2d-fb/README.md)); options off: [`tests/experimental/options-off/run.sh`](../../../../tests/experimental/options-off/run.sh) |
| **Upstream** | not reported yet |

## In short

ROMS splits the flow into a fast barotropic (depth-averaged) mode and the
slow 3-D flow. The fast mode takes many short steps (`NDTFAST`) within each
3-D step. COAWST uses ROMS's LF-AM3 scheme for them: a leapfrog predictor
and an Adams-Moulton corrector, so two kernel calls per fast step, plus an
auxiliary step at the end. Shchepetkin & McWilliams (2005, Sec. 2.3)
describe a generalized forward-backward scheme, AB3-AM4, that needs one call
per fast step and is stable to a barotropic Courant number of about 0.89.
ROMS and COAWST v3.9 carry this kernel (`step2d_FB.h`) as an unfinished port
that is never compiled. The patch completes it for COAWST, including the
wave-current interaction and vegetation terms, behind the cpp option
`STEP2D_FB_AB3_AM4`.

Switch it on with `#define STEP2D_FB_AB3_AM4` in the case header, or
`--build-arg CPP_OPTIONS="+STEP2D_FB_AB3_AM4"`. Use the same `NDTFAST` as
with LF-AM3 as long as the barotropic Courant number
C = sqrt(g h) dt_fast sqrt(1/dx² + 1/dy²) stays below about 0.85.

## Background: why the shipped kernel could not be used

`step2d.F` always includes `step2d_LF_AM3.h`. The shipped `step2d_FB.h` (as
in Rutgers ROMS, which does not compile it either):

- cycles the free surface and barotropic velocity through four time levels,
  but `mod_ocean.F` allocates three (it would write out of bounds);
- uses `rufrc_bak`, which no module declares, and declares diagnostic
  arrays that `step2d` never passes (it would not compile);
- takes the 2-D pressure gradient's density factor as `1 + rhoS`, where
  ROMS's `rhoS` is relative to 1000 kg/m³ and LF-AM3 uses `1000/rho0 + rhoS`
  (2.4 % error with varying density);
- exchanges the time averages `Zt_avg1`, `DU_avg1`, `DV_avg1` across tiles
  only with `NESTING`, though the 3-D step reads `DU_avg1` in the halo;
- removes the 3-D bottom drag from the forcing assuming a linear drag and
  redoes it implicitly (wrong for `SSW_BBL` and quadratic drag);
- `wetdry.F` averages the wet/dry masks over predictor and corrector calls
  and sets the 3-D masks in the auxiliary step, which AB3-AM4 does not have;
- writes debug output to unit 20 every fast step;
- has none of COAWST's wave terms (Stokes transport, the wave pressure terms
  `zetaw`, `qsp`, `bh`, their diagnostics) or vegetation drag.

## The change

- `step2d.F`: includes `step2d_FB.h` with the option. It stops the build
  (`#error`) for combinations not ported: 2-D runs (no `SOLVE3D`),
  `NESTING`, `STEP2D_CORIOLIS`, and `STEP2D_FB_LF_AM3`.
- `mod_ocean.F`: `zeta`, `ubar`, `vbar` get four time levels with the option.
- `step2d_FB.h`, rewritten for 3-D runs:
  - every fast step: the free surface from the transport including the
    Stokes transport (with LF-AM3's `WET_DRY` masking of it), so `DU_avg2` is
    the Lagrangian transport and `DU_avg1` the Eulerian one, as `step3d_uv.F`
    expects; the pressure gradient at the AM4-interpolated free surface
    (density factor as LF-AM3) plus the `WEC_VF` wave pressure terms; 2-D
    climatology nudging as LF-AM3;
  - also every fast step, with LF-AM3's code: momentum advection (4th or
    2nd order) by the Lagrangian fluxes, Coriolis and Stokes-Coriolis,
    curvilinear terms and the `WEC_VF` vortex force, at the extrapolated
    velocity. Their depth integrals are also in the 3-D forcing, so, as in
    LF-AM3, their values at the first fast step are subtracted from it: they
    act through their change during the fast steps;
  - viscosity, wave forces (breaking, roller, streaming), bottom stress and
    vegetation drag stay in the 3-D forcing, held for the whole 3-D step at
    time n (as LF-AM3, apart from their small change during the fast steps).
    The Rutgers version extrapolates this forcing to n+1/2; with COAWST's
    AB3 3-D momentum that blew up (below);
  - `DIAGNOSTICS_UV`: every 2-D term as in LF-AM3, integrated over the fast
    steps with `DU_avg1`'s weights;
  - `WET_DRY`: masks from the free surface at the start of each fast step;
    `wetdry.F` averages them over the `nfast` steps;
  - `SED_MORPH`: the bed change applied 1/`nfast` per fast step (compiled,
    not run);
  - after the last fast step all four time levels of `zeta` hold `Zt_avg1`
    (and `step3d_uv.F` puts the barotropic velocity into all four levels of
    `ubar`, `vbar`), so the rest of COAWST (output, SWAN coupling, WEC, the
    bottom boundary layer, diagnostics) sees the same state as after LF-AM3.
- `wetdry.F`: with the option, the mask average is reset at the first fast
  step and the 3-D masks are set after step `nfast`.

## How the design was found

On a realistic whole-island reef case (private: a periodic O-grid round an
island, a reef crest well under a metre deep, waves, tide, GLS turbulence):

- forcing extrapolated to n+1/2 with the Rutgers AB3 weights: blew up within
  half an hour, a grid-scale oscillation along one crest column with the
  vertical Courant number growing by orders of magnitude in a few steps; AB2
  weights also drove it far above 1 at several crest columns; with the
  forcing held at time n it stayed below 1;
- forcing at time n but the advection, Coriolis and vortex-force terms
  frozen for the 3-D step (as Rutgers and UCLA ROMS do): one very shallow
  crest column oscillated around low tide, centimetres of sea level and tens
  of cm/s away from LF-AM3, then decayed;
- those terms recomputed every fast step, as LF-AM3 does: no such event in
  6 h, about a fifth faster than LF-AM3, with results within millimetres of
  sea level and a few cm/s of depth-mean current of it.

## How the test works

`tests/experimental/roms-step2d-fb/run.sh`
([README](../../../../tests/experimental/roms-step2d-fb/README.md)) builds
Reef_Ideal_A15 and Circle_Island with the whole series and ROMS's `PROFILE`
timers, each with LF-AM3 and with the option, and runs each case for 1 h
three ways:

| Run | Scheme | DT, NDTFAST |
|---|---|---|
| `lf` | LF-AM3 | the case's: A15 6 s, 24; Circle 4 s, 10 |
| `fb` | AB3-AM4 | the same |
| `ref` | LF-AM3 | DT and the fast step 4 times smaller: A15 1.5 s, 24; Circle 1 s, 10 |

The barotropic Courant numbers at the case settings are 0.81 (A15) and 0.18
(Circle). Neither scheme is the exact answer, so both are compared with the
reference. The test passes if AB3-AM4 is nowhere more than twice as far from
it as LF-AM3. That the build is unchanged with the option off is the
tier's [options-off test](../../../../tests/experimental/options-off/README.md).

## Engine test results

Run 2026-11-01 on Cloud Batch (c2d-standard-8 Spot; A15 ROMS 1x6 + 2 SWAN,
Circle 6x1 + 2). PASS.

**Accuracy** at 1 h (largest / RMS difference over the domain):

| Case, field | LF-AM3 vs reference | AB3-AM4 vs reference | AB3-AM4 vs LF-AM3 |
|---|---|---|---|
| A15, sea level (m) | 3.9e-4 / 5.8e-5 | 5.7e-4 / 7.8e-5 | 1.8e-4 / 2.5e-5 |
| A15, ubar (m/s) | 5.0e-3 / 2.7e-4 | 5.0e-3 / 2.8e-4 | 3.3e-3 / 1.0e-4 |
| A15, vbar (m/s) | 5.1e-3 / 2.2e-4 | 4.8e-3 / 2.8e-4 | 5.1e-3 / 1.5e-4 |
| A15, v, 3-D (m/s) | 3.7e-2 / 7.8e-4 | 3.7e-2 / 8.3e-4 | 2.0e-2 / 2.9e-4 |
| A15, Hs (m) | 1.1e-3 / 9.4e-5 | 1.5e-3 / 1.0e-4 | 1.3e-3 / 3.7e-5 |
| Circle, sea level (m) | 4.6e-5 / 3.2e-5 | 4.6e-5 / 2.8e-5 | 1.5e-5 / 6.4e-6 |
| Circle, vbar (m/s) | 1.1e-3 / 2.2e-5 | 1.0e-3 / 2.2e-5 | 2.1e-4 / 8.8e-6 |
| Circle, v, 3-D (m/s) | 1.5e-3 / 3.2e-5 | 1.5e-3 / 3.2e-5 | 2.7e-4 / 9.1e-6 |
| Circle, Hs (m) | 3.3e-4 / 8.1e-6 | 3.3e-4 / 1.0e-5 | 1.2e-4 / 5.6e-6 |

(`u` and `ubar` are like `v` and `vbar`; all in `check.txt`.) Both schemes
are the same distance from the reference, within a few per cent at the
largest differences and about 10 % in RMS (AB3-AM4 slightly further on A15's
sea level and Hs, slightly closer on Circle's sea level). Their difference
from each other is smaller than either's from the reference.

**Speed** (ROMS's `PROFILE`, CPU seconds summed over the 6 ROMS processes,
1 h):

| | A15 LF-AM3 | A15 AB3-AM4 | Circle LF-AM3 | Circle AB3-AM4 |
|---|---|---|---|---|
| 2-D kernel | 281 | **110** | 162 | **68** |
| 2-D halo exchanges | 75 | 43 | 29 | 21 |
| waiting for SWAN | 190 | 324 | 147 | 199 |
| all of ROMS | 917 | 868 | 821 | 790 |
| wall time (s) | 157 | 150 | 139 | 133 |

The 2-D kernel takes 2.4-2.6x less time and its halo exchanges 1.4-1.7x
less. Here the time saved goes into waiting for SWAN, whose 2 processes
set the pace, so the wall time changes by only 4-5 %. The wall-time gain
needs a process split in which ROMS, not SWAN, is the slower side: on the
private realistic case (more SWAN processes) it was about a fifth.

**Options off**: every patched file preprocesses to the same Fortran with and
without the patch, except two `__LINE__` numbers passed to ROMS's timer in
`step3d_uv` ([options-off test](../../../../tests/experimental/options-off/README.md),
four configurations including `WET_DRY`).

## Limits and what has not been checked

- 3-D runs only; not with `NESTING`, `STEP2D_CORIOLIS` or
  `STEP2D_FB_LF_AM3` (the build stops).
- `SED_MORPH` is compiled but has not been run with the option.
- Its stability limit (Courant number about 0.89 in theory, 0.85 to be safe)
  is lower than LF-AM3's; a case running LF-AM3 near its own limit may need a
  larger `NDTFAST`.
- Accuracy is measured against a reference with smaller time steps on two
  idealized cases (above); on stratified flows it has been run only on the
  private case (a heated, stratified variant: salinity, uniform there, stayed
  uniform to the last digit, and temperature stayed close to LF-AM3's).

## Who is affected

Nobody unless the option is defined. With it: any 3-D COAWST run, faster in
proportion to how much of its time the barotropic kernel takes.
