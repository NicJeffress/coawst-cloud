# roms-diag-implicit-drag.patch: the momentum budget closes with implicit drag

| | |
|---|---|
| **Type** | experimental (acts with `DIAGNOSTICS_UV` and `BSTRESS_IMPLICIT` or `VEG_DRAG_IMPLICIT`) |
| **Changes results?** | output only: the diagnostics file. The solution is bit-identical |
| **Default** | on, inside those options |
| **Files** | `ROMS/Nonlinear/step3d_uv.F`, `step2d_FB.h`, `step2d_LF_AM3.h` |
| **Evidence** | idealized reef, 2 h: 2-D and 3-D budget residuals about 1e-7 of the largest term (single-precision output); history bit-identical to a build without the patch |
| **Test** | [`tests/experimental/roms-diag-implicit-drag`](../../../../tests/experimental/roms-diag-implicit-drag/README.md) |
| **Upstream** | not proposed (these options are this repository's) |

## What was wrong

`roms-bstress-implicit` and `roms-veg-implicit` take the drag in the denominator
of the velocity update. The diagnostics, written for an explicit right-hand
side, did not see it:

1. **`ubar_bstr`, `vbar_bstr` held only the explicit remainder** `rbu`. The implicit
   part `c2bu ubar` was missing: 0.001 where about 0.6 was needed across a bare
   reef (m³/s² per metre alongshore).
2. **The canopy drag was missing from the 2-D budget** and, in 3-D, was mixed
   into `u_vvis`, `v_vvis`, measured as the change across the tridiagonal solve.
3. **The 3-D `M3fveg` term was never coupled to the barotropic one.** `step3d_uv`
   corrects each 3-D term so that its depth integral equals the 2-D term, but never
   set `Dwrk(:,M2fveg)` (also in stock COAWST, where the value is unused).
4. **In `step2d_LF_AM3.h` `DiaU2rhs(:,:,M2fveg)` was never set** with
   `VEG_DRAG_IMPLICIT` (that kernel has no zeroing loop, unlike `step2d_FB.h`). The
   garbage stayed among the diagnostic arrays and never reached the solution; a
   run stopped with NetCDF error -60 once `vbar_fveg` was switched on.

## The change

- **2-D, AB3-AM4 (`step2d_FB.h`):** after the update, adds `-c2u_veg ubar_new A` to
  `M2fveg` and `-c2bu ubar_new A` to `M2bstr`, with A the cell area
  4/((pm+pm')(pn+pn')). These are the terms in the denominator, in the units of `DiaU2rhs`.
- **2-D, LF-AM3 (`step2d_LF_AM3.h`):** zeroes `M2fveg`; adds both to `DiaU2int` and
  `DiaU2wrk` in the corrector with their full weight, not the AM3 weights.
- **3-D (`step3d_uv.F`):** in the tridiagonal solve, moves `-dt cu_veg u_new/Hz` from
  `M3vvis` to `M3fveg`, level by level; sets `Dwrk(:,M2fveg)` and couples `M3fveg`.

After it, `u_vvis`, `v_vvis` hold vertical viscosity and bottom and surface
stress, as in standard ROMS, with the bed stress in the bottom layer; their depth
integral equals `ubar_bstr` plus `ubar_sstr`. `u_fveg`, `v_fveg` hold the canopy drag.

## Switching the output on

The canopy terms are read from `vegetation.in`, not `ocean.in`:

```
Dout(M2fveg) == T
Dout(M3fveg) == T
```

Without these lines `*_fveg` are not written and the canopy drag is in no term.

## Limits

- `DiaU2rhs(M2bstr)` is the stress the barotropic mode feels. With `BSTRESS_IMPLICIT`
  this is `bustr` at the start of the step plus the implicit correction.
- The diagnostics file grows by two 2-D and two 3-D variables.
