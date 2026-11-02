# roms-bstress-implicit.patch: implicit bottom stress (the full stress, taken stably)

| | |
|---|---|
| **Type** | experimental (cpp option `BSTRESS_IMPLICIT`, with `SSW_BBL`) |
| **Changes results?** | with the option: the bottom stress is taken backward Euler, without `LIMIT_BSTRESS`'s cap. Without it: the build is unchanged |
| **Default** | off. **Use it where `LIMIT_BSTRESS` would bind** (a thin bottom layer under fast flow: reef crests tens of centimetres deep). On thin-crest variants of Reef_Ideal_A15 it matches the uncapped explicit stress to 1 % where the cap halves the friction. On one realistic grid runs with it failed, but so did runs with the capped explicit stress on that grid (see below) |
| **Files** | `ROMS/Nonlinear/BBL/ssw_bbl.h`, `pre_step3d.F`, `rhs3d.F`, `step3d_uv.F`, `step2d_LF_AM3.h`, `step2d_FB.h`; `ROMS/Modules/mod_forces.F` |
| **Evidence** | Reef_Ideal_A15 and Circle_Island, 1 h: runs, currents within 5 cm/s of the explicit stress at 99.9 % of cells. Thin-crest A15 variants (0.30 m crest, slope factor up to 0.41), 3 h through low tide: crest current and set-up within 1 % of the uncapped explicit stress; the capped stress gives 40-75 % faster crest flow. A realistic case with a 0.30 m crest: failed, as did the capped explicit stress; on its smoothed grid it ran day-long cases. Options off: same preprocessed Fortran |
| **Test** | [`tests/experimental/roms-bstress-implicit/run.sh`](../../../../tests/experimental/roms-bstress-implicit/run.sh) and the thin-crest runs [`thin_crest.sh`](../../../../tests/experimental/roms-bstress-implicit/thin_crest.sh) ([README](../../../../tests/experimental/roms-bstress-implicit/README.md)); options off: [`tests/experimental/options-off/run.sh`](../../../../tests/experimental/options-off/run.sh) |
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
layer thickness and time step, so the full stress can be applied. Where the
explicit stress is stable the option reproduces it (thin-crest A15 variants:
crest current and set-up within 1 %); where the cap would bind it applies the
full stress instead of the cap's fraction of it. On the realistic case it was
written for, runs failed on the grid as built, but so did runs with the
capped explicit stress; on that case's smoothed grid it ran day-long
simulations.

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

On the private whole-island case it was written for (crest 0.30 m deep, two
10 m rows wide, slope factor rx0 0.40 on both flanks, ten levels;
`LIMIT_BSTRESS` otherwise needed), every run with the full implicit stress
failed within the first 40 minutes, also with `OMEGA_IMPLICIT` and with DT
reduced to a half or a third: the surface layer ran away at the crest and at
the ends of crest segments beside channels, with vertical Courant numbers
rising to 5-20 within a few steps. **The capped explicit stress failed on the
same grid at the same place** (30 minutes against 39 with the option), so the
failure belongs to that grid, not to the option. The cause was not found. A
uniform breaking-force profile (`3-experimental/wec-break-uniform`) was tried
as a hypothesis and did not change the outcome. With the crest deepened to
0.40 m and the slopes limited to rx0 0.2, the option ran five day-long cases
with the full friction, which mainly lowered the crest jet (about a third off
its peak) and left the reef-wide circulation, waves and temperatures within a
few per cent of the capped runs.

## Thin-crest variants of Reef_Ideal_A15 (2026-11-02)

To find out whether the full stress on a thin crest is what fails,
`thin_crest.sh` runs A15 with its crest changed by `make_thin_crest.py` (ROMS
grid and SWAN bathymetry; only the reef columns change):

| grid | crest | flanks (rx0) |
|---|---|---|
| default_1 | 0.50 m, four 20 m rows | 0.34 |
| thin_smooth | 0.30 m, four rows | eased, <= 0.32 |
| thin_steep | 0.30 m, two rows, 0.71 m either side | 0.41 (the realistic crest's profile) |
| steep_050 | 0.50 m, two rows, 1.19 m either side | 0.41 |

Three builds, all with `-SPLINES_VVISC`: `cap` (+LIMIT_BSTRESS), `nocap`
(the explicit stress as shipped) and `imp` (+BSTRESS_IMPLICIT); 3 h each
through low tide (0.15 m of water over the thin crests), DT 6 s, Hs 1 m,
ROMS 1x6 + 2 SWAN on Cloud Batch. All twelve runs finished. At 3 h:

| grid | scheme | fastest current (m/s) | largest vertical Courant | crest depth-mean current (m/s) | lagoon set-up (mm) |
|---|---|---|---|---|---|
| default_1 | cap / nocap / imp | 1.14 / 1.01 / 1.00 | 0.54 / 0.46 / 0.44 | 0.58 / 0.50 / 0.50 | 53.5 / 42.0 / 41.4 |
| thin_smooth | cap / nocap / imp | 1.48 / 0.95 / 0.94 | 1.56 / 0.76 / 0.75 | 0.98 / 0.56 / 0.56 | 32.4 / 16.1 / 16.0 |
| thin_steep | cap / nocap / imp | 1.17 / 0.91 / 0.92 | 2.03 / 1.21 / 1.21 | 1.12 / 0.79 / 0.79 | 43.3 / 26.1 / 26.2 |
| steep_050 | cap / nocap / imp | 1.11 / 1.06 / 1.05 | 0.77 / 0.65 / 0.66 | 0.56 / 0.53 / 0.52 | 51.3 / 46.3 / 45.6 |

- The option and the uncapped explicit stress agree to 1 % on every grid:
  the option changes only the time discretization.
- The cap is the scheme that differs. It binds at 51-67 % of the crest cells
  (`cap_stats.py`: stability number S = tau DT / (Hz_1 |u_1|) held at 0.75)
  and halves the effective drag there: on thin_steep the median crest stress
  is 1.75 N m⁻² at a bottom-layer speed of 0.32 m/s with the cap, 2.12 N m⁻²
  at 0.24 m/s without it. The crest flow is 15 % faster on the 0.50 m crest
  and 40-75 % faster on the 0.30 m crests, the set-up 25-100 % higher.
- The explicit stress is stable far beyond the cap's criterion: without the
  cap the crest runs at S median 1.4-1.9, 90th percentile 3-6, largest 7-11,
  for 3 h. The vertical viscosity ties the thin bottom layer to the layers
  above within a step, so the layer that sets the stability limit is thicker
  than Hz_1. `LIMIT_BSTRESS` (and `WET_DRY`, which carries it in COAWST) is
  more conservative than needed here, at a large cost in friction.
- Converged in DT: at DT 3 s the option and the uncapped explicit stress
  change by 0.3-0.5 % in crest current and 0.1 mm in set-up, and still agree
  with each other. ROMS's AB3-AM4 barotropic kernel
  (`3-experimental/roms-step2d-fb`) gives the same numbers as LF-AM3 for both
  schemes.
- The realistic case's runaway is not reproduced on the crest: a 0.30 m
  crest, rx0 0.41 flanks, and both together run with every scheme, through
  low tide. A 2 m sea switched on at t = 0 without a ramp does blow the
  thin_steep grid up, but with all three schemes within three minutes of
  each other (the capped one first), in the jet through the pass at
  mid-depth, not on the crest: a forcing shock, with no scheme dependence.
  With the same sea ramped up over an hour, all three schemes run 3 h
  through low tide at DT 6 and 3 s.
- **The cap makes the answer depend on the time step.** Its limit,
  0.75 Hz₁ |u₁| / DT, doubles when DT is halved: in the ramped 2 m runs the
  capped set-up falls from 179 to 151 mm and the crest flow from 1.22 to
  1.10 m/s between DT 6 and 3 s, towards the uncapped answer (140 mm,
  1.05 m/s) from above. The option and the uncapped explicit stress change by
  0.1 % between the two steps and agree with each other to 0.8 %.
- The remaining differences from the realistic case are its 10 m rows and
  crest segments that end at channels.

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

- The failure on the realistic grid (which the capped explicit stress shares)
  is unexplained and not reproduced on an idealized grid.
- Accuracy: on the default A15 grid an earlier integral comparison (lagoon
  set-up, crest flow) found the option converged in DT (6 against 3 s) and
  within about 2.5 % of the explicit stress; the thin-crest runs above agree
  to 1 % at DT 6 s.
- `SSW_BBL` only, and not with `SPLINES_VVISC`.
- The failure on the realistic case was not reproduced on an idealized case.

## Who is affected

Nobody unless the option is defined.
