# wec-break-uniform.patch: breaking force spread evenly over depth (sensitivity switch)

| | |
|---|---|
| **Type** | experimental (cpp option `WEC_BREAK_UNIFORM`, with `WEC_VF`) |
| **Changes results?** | with the option: the depth-integrated wave-breaking force is unchanged but distributed evenly over the water column instead of concentrated near the surface. Without it: the build is unchanged |
| **Default** | off |
| **Files** | `ROMS/Nonlinear/WEC/wec_vf.F` |
| **Evidence** | Reef_Ideal_A15, 1 h: breaking acceleration top/bottom layer ratio 188 by default, 0.998 with the option, at the 50 strongest points; currents change by up to 14 cm/s at the surface; options off: same preprocessed Fortran |
| **Test** | [`tests/experimental/wec-break-uniform/run.sh`](../../../../tests/experimental/wec-break-uniform/run.sh) ([README](../../../../tests/experimental/wec-break-uniform/README.md)); options off: [`tests/experimental/options-off/run.sh`](../../../../tests/experimental/options-off/run.sh) |
| **Upstream** | not proposed (a test switch) |

## In short

With `WEC_VF`, COAWST turns SWAN's breaking dissipation into a body force on
the currents (`wec_vf.F`). Its vertical profile is cosh(2π γ (z - z_bottom)
/ D), normalized so that its depth integral is the dissipation divided by the
wave celerity, with γ = min(1.414 D / (1.25 Hs), 1): in shallow, strongly
breaking water (D small compared with Hs, γ ≈ 1) most of the force goes into
the upper layers. The option sets γ = 0, which makes the profile cosh(0) = 1:
the same total force, spread evenly over depth.

It is a switch for sensitivity tests: how much does a result depend on the
assumed vertical distribution of breaking? It was added to test whether the
surface-intensified force caused the failure of
`3-experimental/roms-bstress-implicit` on a realistic reef (it did not).

## The change

In `wec_vf.F`, after γ (`gamr`) is computed:

```fortran
#ifdef WEC_BREAK_UNIFORM
!  Test option (3-experimental/wec-break-uniform.patch): breaking
!  force spread evenly over the water column (cosh(0) = 1) instead of
!  concentrated near the surface.
          gamr(i,j)=0.0_r8
#endif
```

In `wec_vf.F` γ is used only for this profile and its normalization; the
roller force (`WEC_ROLLER`) uses the same profile, so the option makes it
uniform too. `wec_roller.F` and `wec_wave_mix.F` compute their own γ, which
the option does not change.

## How the test works

`tests/experimental/wec-break-uniform/run.sh`
([README](../../../../tests/experimental/wec-break-uniform/README.md)) builds
Reef_Ideal_A15 (whose header has `DIAGNOSTICS_UV`) without and with the
option and runs each for 1 h. At the 50 v-points with the strongest
depth-integrated breaking acceleration (`v_wbrk` in `ocean_dia.nc`) it takes
the ratio of the top-layer to the bottom-layer acceleration. It passes if the
ratio is 1 within 1 % with the option and above 2 (median) without.

## Engine test results

Run 2026-11-01 on Cloud Batch (c2d-standard-8 Spot, ROMS 1x6 + 2 SWAN). PASS.

| | Default | `WEC_BREAK_UNIFORM` |
|---|---|---|
| breaking acceleration, top / bottom layer (50 strongest points) | 188 (187.6-188.0) | 0.998 (all 50) |

(Not exactly 1: the acceleration at a v-point averages the force of its two
neighbouring columns, weighted by their layer thicknesses.) The change in
the currents after 1 h:

| | largest difference | largest value (default) |
|---|---|---|
| depth-mean, ubar / vbar | 8.8 / 7.5 cm/s | 0.47 / 0.97 m/s |
| surface layer, u / v | 13.8 / 9.8 cm/s | |
| bottom layer, u / v | 5.4 / 5.2 cm/s | |

So on A15's crest the assumed vertical distribution of breaking moves the
depth-mean current by up to about 10 % and the surface current more.

**Options off**: the patched file preprocesses to the same Fortran with and
without the patch ([options-off test](../../../../tests/experimental/options-off/README.md)).

## Who is affected

Nobody unless the option is defined.
