# roms-veg-implicit.patch: implicit canopy drag

| | |
|---|---|
| **Type** | experimental (cpp option `VEG_DRAG_IMPLICIT`, with `VEGETATION` and `VEG_DRAG`) |
| **Changes results?** | with the option: the canopy drag is taken backward Euler, which removes its time-step limit; results differ from the explicit drag by that time discretization. Without it: the build is unchanged |
| **Default** | off |
| **Files** | `ROMS/Nonlinear/Vegetation/vegetation_drag.F`, `vegetation_mod.h`; `ROMS/Nonlinear/rhs3d.F`, `step3d_uv.F`, `step2d_LF_AM3.h`, `step2d_FB.h` |
| **Evidence** | Reef_Ideal_A15_veg with a patchy canopy, 1 h: explicit drag at DT 6 s blows up between 40 and 50 min; implicit at DT 6 s runs and stays within 1 cm/s of the explicit DT 3 s reference at 99.9 % of cells; options off: same preprocessed Fortran (except one comment line) |
| **Test** | [`tests/experimental/roms-veg-implicit/run.sh`](../../../../tests/experimental/roms-veg-implicit/run.sh) ([README](../../../../tests/experimental/roms-veg-implicit/README.md)); options off: [`tests/experimental/options-off/run.sh`](../../../../tests/experimental/options-off/run.sh) |
| **Upstream** | not reported yet |

## In short

COAWST's canopy (vegetation) drag, c |U| u with c = 0.5 Cd D n inside the
canopy (Cd drag coefficient, D plant diameter, n plants per m²), is added to
the 3-D right-hand side, which is stepped with AB3, and its depth integral
is handed to the barotropic mode frozen for a whole 3-D step. Both are
explicit, so a run becomes unstable once 2 c |U| DT is well above 1. A dense
canopy (c = 1 m⁻¹) with currents near 1 m/s allows only DT of about 1 s;
patchy reefs, where fast flow from bare gaps runs into dense patches, are
the worst case.

With the option the drag is taken backward Euler, in the 3-D step and at
every barotropic step, which is stable for any time step.

## Background: the explicit limit

For du/dt = -c |U| u, an explicit step multiplies u by (1 - c |U| dt) per
step, stable while c |U| dt < 2 for forward Euler and less for AB3 (whose
stability region on the negative real axis reaches 6/11). A backward Euler
step divides u by (1 + c |U| dt): it can only damp, whatever the time
step. |U| is taken at the start of the 3-D step, which linearizes the drag.

## The change

- `vegetation_drag.F` also stores per layer `cu_veg` = c Hz |U| (m/s), so
  that c Hz |U| u is the drag of that layer per unit area, and a barotropic
  coefficient `c2u_veg` with `c2u_veg * ubar` equal to the depth-integrated
  drag when it is computed (so the canopy's own velocity profile is kept;
  sum(`cu_veg`) where ubar is below 1e-4 m/s or the ratio is not positive;
  at most 2 sum(`cu_veg`)). `ru_veg`/`rv_veg` are still computed (canopy
  turbulence `VEG_TURB`, output).
- `rhs3d.F` leaves the drag out of the 3-D right-hand side, and so out of the
  barotropic mode's 3-D forcing.
- The barotropic kernels take the drag backward Euler at every fast step:
  `2 dt c2u` is added to the denominator `2 D` of each ubar/vbar update, with
  that update's own dt (`step2d_LF_AM3.h`: the first step, the leapfrog
  predictor and the AM3 corrector; `step2d_FB.h` with `STEP2D_FB_AB3_AM4`).
  LF-AM3's explicit 2-D drag term is dropped, the 3-D integral no longer
  holding the drag.
- `step3d_uv.F`: in every layer u = u / (1 + dt cu_veg/Hz) after the implicit
  vertical viscosity (with `SPLINES_VVISC`, as in the test case); the depth
  mean is then replaced by the barotropic one as always. Without
  `SPLINES_VVISC`, the next patch in the series (`roms-bstress-implicit`)
  puts `dt cu_veg` into the diagonal of the tridiagonal vertical-viscosity
  solve instead, so drag and mixing are solved together.
- `vegetation_mod.h`: the new arrays.

`DIAGNOSTICS_UV` does not report the drag term with the option.

## How the test works

`tests/experimental/roms-veg-implicit/run.sh`
([README](../../../../tests/experimental/roms-veg-implicit/README.md)) uses
Reef_Ideal_A15_veg (waves, tide, GLS, canopy drag and canopy turbulence)
with a patchy canopy written by the case's `make_patchy_init.py`: over the
backreef, crest and forereef, 30 % of the area dense plants (4 m⁻², so
0.5 Cd D n = 1 m⁻¹), 30 % sparse (1 m⁻²), 40 % bare, in patches of about
150 m. It builds the case (whole series) without and with the option and runs
each for 1 h (ROMS 1x6 + 2 SWAN):

| Run | Drag | DT |
|---|---|---|
| `patchy-exp-dt6` | explicit | 6 s (the case's) |
| `patchy-imp-dt6` | implicit | 6 s |
| `patchy-exp-dt3` | explicit | 3 s: the reference |
| `patchy-imp-dt3` | implicit | 3 s |
| `const-exp-dt6`, `const-imp-dt6` | explicit / implicit | 6 s, the case's uniform canopy |

It passes if all implicit runs and both references finish and the implicit
DT 6 s run is within 2 cm/s of the reference at 99.9 % of the cells.

## Engine test results

Run 2026-11-01 on Cloud Batch (c2d-standard-8 Spot). PASS.

| Run | Outcome | Wall time |
|---|---|---|
| patchy, explicit, DT 6 s | **blew up between 40 and 50 min** | |
| patchy, implicit, DT 6 s | ran 1 h | 160 s |
| patchy, explicit, DT 3 s (reference) | ran | 210 s |
| patchy, implicit, DT 3 s | ran | 211 s |
| uniform canopy, explicit / implicit, DT 6 s | ran | 156 / 158 s |

Differences at 1 h (depth-mean current at rho points, 21708 wet cells):

| Comparison | largest | 99.9 % of cells within | cells > 1 cm/s | RMS diff / RMS speed | sea level | Hs |
|---|---|---|---|---|---|---|
| patchy, implicit DT 6 s vs explicit DT 3 s | 1.4 cm/s | 1.0 cm/s | 20 | 1.3 % | 2.1 mm | 2 mm |
| patchy, implicit DT 3 s vs explicit DT 3 s | 1.1 cm/s | 0.6 cm/s | 1 | 0.9 % | 1.6 mm | 2 mm |
| uniform canopy, implicit vs explicit, DT 6 s | 1.0 cm/s | 0.3 cm/s | 0 | 1.7 % | 0.2 mm | < 1 mm |

So the option removes the time-step limit, changes the currents by about a
centimetre per second at most, and runs the patchy reef at DT 6 s (160 s for
1 h here; the explicit drag needs DT 3 s, 210 s). The gain in wall time is
smaller than the halved step count because SWAN, on 2 processes, sets the
pace.

**Options off**: the patched files preprocess to the same Fortran with and
without the patch, except one comment line in `vegetation_drag`
([options-off test](../../../../tests/experimental/options-off/README.md)).

## Limits and what has not been checked

- |U| is taken at the start of the 3-D step (linearized drag): the implicit
  drag is stable, but its accuracy at large c |U| DT depends on how fast |U|
  changes within a step.
- `DIAGNOSTICS_UV` has no drag term with the option.
- Flexible plants (`VEG_FLEX`) are not covered by the tests.

## Who is affected

Nobody unless the option is defined. With it: runs with canopy drag, which
can then use the time step the rest of the flow allows.
