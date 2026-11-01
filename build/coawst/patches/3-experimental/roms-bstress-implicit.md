# roms-bstress-implicit.patch: implicit bottom stress (a negative result)

| | |
|---|---|
| **Type** | experimental (cpp option `BSTRESS_IMPLICIT`, with `SSW_BBL`) |
| **Changes results?** | with the option: the bottom stress is taken backward Euler, without `LIMIT_BSTRESS`'s cap. Without it: the build is unchanged |
| **Default** | off; **not recommended**: on a realistic shallow reef case every run with it failed |
| **Files** | `ROMS/Nonlinear/BBL/ssw_bbl.h`, `pre_step3d.F`, `rhs3d.F`, `step3d_uv.F`, `step2d_LF_AM3.h`, `step2d_FB.h`; `ROMS/Modules/mod_forces.F` |
| **Evidence** | Reef_Ideal_A15 and Circle_Island, 1 h: runs, currents within 5 cm/s of the explicit stress at 99.9 % of cells; a realistic case with a crest tens of centimetres deep: every run failed; options off: same preprocessed Fortran |
| **Test** | [`tests/experimental/roms-bstress-implicit/run.sh`](../../../../tests/experimental/roms-bstress-implicit/run.sh) ([README](../../../../tests/experimental/roms-bstress-implicit/README.md)); options off: [`tests/experimental/options-off/run.sh`](../../../../tests/experimental/options-off/run.sh) |
| **Upstream** | not reported (not proposed) |

## In short

ROMS applies the bottom stress explicitly: as a flux dt × bustr into the
bottom layer (`pre_step3d.F`) and as -bustr in the barotropic mode's 3-D
forcing (`rhs3d.F`), frozen for a 3-D step. Where the bottom layer is thin
and the flow fast, that is stable only with `LIMIT_BSTRESS`, which caps
|τ_b| at 0.75 Hz₁ |u₁| / dt (see `1-fixes/roms-limit-bstress`). On a very
shallow crest (tens of centimetres, ten layers) the cap binds over most of a
fast reef-crest jet and leaves the friction there several times below the
log law with the case's roughness: the cap is set by the layer thickness and
the time step, not by the roughness.

This option takes the stress backward Euler instead, which is stable for any
layer thickness and time step, so the full stress can be applied. It is kept
in the engine as a documented negative result: it runs on Reef_Ideal_A15,
but on the realistic case it was written for no run survived.

## The change

- `ssw_bbl.h` computes the stress as before but skips the cap, and stores
  kbu = |bustr| / |u₁| (m/s; |u₁| at least 1e-4 m/s; where u₁ alone is near
  zero, from the critical stress) and a barotropic coefficient c2bu = kbu u₁
  / ubar (kbu where ubar is below 1e-4 m/s or the ratio is not positive; at
  most 2 kbu). `bustr` itself remains the full stress (output, sediment,
  coupler).
- `pre_step3d.F`: no explicit bottom flux; `rhs3d.F`: no -bustr in the 3-D
  forcing.
- `step3d_uv.F`: `dt kbu` is added to the bottom layer's diagonal of the
  tridiagonal vertical-viscosity solve, so bottom drag and vertical mixing
  are solved together (and `dt cu_veg` to every layer's, with
  `VEG_DRAG_IMPLICIT`). This needs the tridiagonal solver: with
  `SPLINES_VVISC` the build stops.
- `step2d_LF_AM3.h`, `step2d_FB.h`: 2 dt c2bu added to the denominator of
  every ubar/vbar update, with that update's dt.
- `mod_forces.F`: the new arrays.
- With the option and any bottom-stress scheme other than `SSW_BBL`, or with
  `SPLINES_VVISC`, the build stops (`#error`) rather than run without bottom
  friction.

## What happened on the realistic case

On the private whole-island case it was written for (crest a few tens of
centimetres deep, `LIMIT_BSTRESS` otherwise needed), every run with the full
implicit stress failed within the first half hour, also with
`OMEGA_IMPLICIT` and with DT reduced to a half or a third: the surface layer
ran away at the crest and the channel edges. The cause was not found. A
uniform breaking-force profile (`3-experimental/wec-break-uniform`) was tried
as a hypothesis and did not change the outcome.

## How the test works

`tests/experimental/roms-bstress-implicit/run.sh`
([README](../../../../tests/experimental/roms-bstress-implicit/README.md))
builds, all with `-SPLINES_VVISC` (which the option requires), Reef_Ideal_A15
without and with the option (A15 has no cap) and Circle_Island with
`+LIMIT_BSTRESS` (the cap the option replaces) and with the option, and runs
each for 1 h. It records whether the runs finish and how much the option
changes them; it passes if the A15 runs finish. It is not an accuracy test.

## Engine test results

Run 2026-11-01 on Cloud Batch (c2d-standard-8 Spot). PASS (as a record).

| Comparison at 1 h | Both finished | Current difference: largest / 99.9th pct | Sea level | Hs | Bottom stress, 99.9th pct (N m⁻²) |
|---|---|---|---|---|---|
| A15, explicit vs implicit | yes | 7.0 / 4.6 cm/s | 3.5 mm | 1.1 cm | 6.23 / 6.25 |
| Circle_Island, capped vs implicit | yes | 5.1 / 4.7 cm/s | 2.8 mm | 0.3 cm | 1.30 / 1.29 |

On both idealized cases the option runs and changes the bottom stress
little; the currents differ by a few cm/s, the size of the stress's time
discretization at these steps. Neither case has a crest thin enough for the
cap to bind much (Circle's crest is 0.8 m deep), so neither reproduces the
failure of the realistic case.

**Options off**: the patched files preprocess to the same Fortran with and
without the patch ([options-off test](../../../../tests/experimental/options-off/README.md)).

## Limits and what has not been checked

- Not recommended: the failure on the realistic case is unexplained.
- Accuracy against a converged reference has not been established on any
  case.
- `SSW_BBL` only, and not with `SPLINES_VVISC`.
- The failure on the realistic case was not reproduced on an idealized case.

## Who is affected

Nobody unless the option is defined.
