# roms-limit-bstress.patch: the bottom-stress limiter follows LIMIT_BSTRESS, not WET_DRY

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no for every existing build (with `WET_DRY` it compiles exactly as before); it makes a new combination possible: the limiter without wetting and drying (`-WET_DRY +LIMIT_BSTRESS`) |
| **Default** | on |
| **Files** | `ROMS/Nonlinear/BBL/ssw_bbl.h`, `sg_bbl.h`, `mb_bbl.h` (two blocks each), `ROMS/Nonlinear/set_vbc.F` (seven) |
| **Evidence** | compile-time test: preprocessed Fortran identical with `WET_DRY`; with `-WET_DRY +LIMIT_BSTRESS` the limiter is absent stock and present patched (results below) |
| **Test** | [`tests/fixes/roms-limit-bstress/run.sh`](../../../../tests/fixes/roms-limit-bstress/run.sh) |
| **Upstream** | not yet reported to COAWST |

## Summary

ROMS can cap the bottom stress so that, within one baroclinic time step, it
can slow the velocity of the bottom layer but never reverse it:

    |tau_b| <= 0.75 * Hz_1 * |u_1| / DT

(`Hz_1` the bottom-layer thickness, `u_1` its velocity, `DT` the time step;
"0.75 is arbitrary" says the source). The bottom stress is applied
explicitly, so where the bottom layer is thin and the drag large, an uncapped
stress can overshoot and flip the flow, and the model goes unstable. The
limiter keeps such runs stable, at the price of friction below the drag law
wherever it binds.

Rutgers ROMS has this limiter as the option `LIMIT_BSTRESS`. COAWST v3.9
defines `LIMIT_BSTRESS` whenever `WET_DRY` is on (`ROMS/Include/globaldefs.h`),
but then tests `WET_DRY` itself in all 13 places that apply the cap, with the
comment "For COAWST, I use WET_DRY in place of the LIMIT option". So in COAWST
the limiter could not be had without wetting and drying, and a case that
switched `WET_DRY` off (because nothing in it dries, say) silently lost the
limiter too.

## The fix

The 13 `#ifdef WET_DRY` lines that guard the cap become
`#ifdef LIMIT_BSTRESS`:

| File | Blocks | Bottom-stress scheme |
|---|---|---|
| `BBL/ssw_bbl.h` | 2 (u and v) | `SSW_BBL` |
| `BBL/sg_bbl.h` | 2 | `SG_BBL` |
| `BBL/mb_bbl.h` | 2 | `MB_BBL` |
| `set_vbc.F` | 7: the factor `cff = 0.75/dt`, and u and v blocks for `UV_LOGDRAG`, `UV_QDRAG`, `UV_LDRAG` | drag laws without a BBL model |

For example, in `ssw_bbl.h`:

```fortran
          bustr(i,j)=0.5_r8*(Tauc(i-1,j)+Tauc(i,j))*anglec
-#ifdef WET_DRY
+#ifdef LIMIT_BSTRESS
           cff2=0.75_r8*0.5_r8*(z_w(i-1,j,1)+z_w(i,j,1)-                 &
      &                         z_w(i-1,j,0)-z_w(i,j,0))
           bustr(i,j)=SIGN(1.0_r8,bustr(i,j))*MIN(ABS(bustr(i,j)),       &
```

Because `WET_DRY` still defines `LIMIT_BSTRESS`, every build with `WET_DRY`
compiles to exactly the same Fortran as before, and builds with neither are
unchanged too. What is new: `-WET_DRY +LIMIT_BSTRESS` in a case header (or in
the build argument `CPP_OPTIONS`) gives the limiter alone.

## When it matters

A case with shallow water but no drying (the shallowest water stays above
the drying threshold `DCRIT`): switching `WET_DRY` off as shipped also removes
the limiter, which can turn a stable run into an unstable one. In shallow
reef cases with a few tens of centimetres of water over the crest, the limiter
can bind in a large share of the cells shallower than 1 m, so it does real
work there. Where it binds, the friction is set by the layer thickness and the
time step rather than the roughness: check how often it binds before trusting
the bottom stress in very shallow water.

## Test

`tests/fixes/roms-limit-bstress/run.sh` builds COAWST's own Veg_test
(`SSW_BBL`, `WET_DRY` on) up to the compile stage, before and after the patch,
as shipped and with `CPP_OPTIONS="-WET_DRY +LIMIT_BSTRESS"`, and compares the
preprocessed Fortran that ROMS compiles (`Build_roms/*.f90`). It is exact and
needs no model run.

1. Patched source: 13 limiter blocks test `LIMIT_BSTRESS`.
2. As shipped (`WET_DRY`): preprocessed Fortran before and after identical.
3. `-WET_DRY +LIMIT_BSTRESS`: no limiter line in the compiled code before the
   patch, the limiter present after it; only the bottom-stress file differs.

## Engine test results

Run 2026-10-30 on the control VM (COAWST 26e6fb7; "before" is the series up to
this patch, `roms-sed-morph-tiling` and `roms-wec-stokes-fixes`):

```
== 1. limiter blocks in the patched source
   blocks testing LIMIT_BSTRESS: 13 (expected 13)
== 2. shipped (WET_DRY): preprocessed Fortran before vs after
   identical (405 files)
== 3. -WET_DRY +LIMIT_BSTRESS: limiter (MIN(ABS(bustr...))) in the compiled code
   before: 0 limiter lines
   after: 2 limiter lines
   files that differ: bbl.f90
PASS
```

The two limiter lines are the u and v blocks of `ssw_bbl.h` (compiled into
`bbl.f90`); nothing else in the 405 compiled files changes.

## Limits

The test covers the `SSW_BBL` blocks in compiled code and all 13 blocks in the
source. The `SG_BBL`, `MB_BBL` and drag-law blocks (`set_vbc.F`) are the same
one-line change; a case using them can be checked the same way.
