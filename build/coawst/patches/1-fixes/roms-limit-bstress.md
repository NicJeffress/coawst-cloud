# roms-limit-bstress.patch: the bottom-stress limiter follows LIMIT_BSTRESS, not WET_DRY

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no for every existing build (with `WET_DRY` it compiles exactly as before); it makes a new combination possible: the limiter without wetting and drying (`-WET_DRY +LIMIT_BSTRESS`) |
| **Default** | on |
| **Files** | `ROMS/Nonlinear/BBL/ssw_bbl.h`, `sg_bbl.h`, `mb_bbl.h` (two blocks each), `ROMS/Nonlinear/set_vbc.F` (seven) |
| **Evidence** | compile-time test: preprocessed Fortran identical with `WET_DRY`; with `-WET_DRY +LIMIT_BSTRESS` the limiter is absent stock and present patched |
| **Test** | [`tests/fixes/roms-limit-bstress/run.sh`](../../../../tests/fixes/roms-limit-bstress/run.sh), see its [README](../../../../tests/fixes/roms-limit-bstress/README.md) |
| **Upstream** | not yet reported to COAWST |

## In short

ROMS can cap the bottom stress so that it never reverses the flow of the
bottom layer within one time step. Rutgers ROMS switches this cap on with the
option `LIMIT_BSTRESS`. COAWST defines `LIMIT_BSTRESS` whenever wetting and
drying (`WET_DRY`) is on, but then, in all 13 places that apply the cap, tests
`WET_DRY` itself instead of `LIMIT_BSTRESS` (its `globaldefs.h` says "For
COAWST, I use WET_DRY in place of the LIMIT option"). So in COAWST the cap could not
be had without wetting and drying: a case that turned `WET_DRY` off (because
nothing in it dries) silently lost the cap too, and could then go unstable in
shallow water. The fix makes those 13 places test `LIMIT_BSTRESS`, which is
what the option is for. Builds with `WET_DRY` are byte-for-byte unchanged.

## Background: why ROMS limits the bottom stress

The bottom stress `tau_b` slows the bottom layer of the flow. ROMS applies it
explicitly: within one baroclinic step of length DT, the bottom-layer
velocity `u_1` changes by `-tau_b DT / Hz_1`, where `Hz_1` is the
bottom-layer thickness. If that change is larger than `u_1` itself, the
stress does not just stop the flow, it reverses it, and the next step reverses
it again, harder: the scheme is unstable. This happens where the bottom layer
is thin (very shallow water, or many levels) and the drag large (fast flow,
rough bed).

The cap prevents it:

    |tau_b| <= 0.75 * Hz_1 * |u_1| / DT

("0.75 is arbitrary", says the source.) Where it binds, the friction is set
by the layer thickness and the time step rather than by the roughness, so
it is weaker than the drag law; but the run stays stable. The alternative, a
smaller time step, costs run time everywhere.

## The bug

COAWST's `ROMS/Include/globaldefs.h` defines `LIMIT_BSTRESS` whenever
`WET_DRY` is on, with the comment "For COAWST, I use WET_DRY in place of the
LIMIT option":

```c
#if !defined LIMIT_BSTRESS && defined WET_DRY
# define LIMIT_BSTRESS
#endif
```

But the code that applies the cap tests `WET_DRY` directly. For example in
`ssw_bbl.h`:

```fortran
          bustr(i,j)=0.5_r8*(Tauc(i-1,j)+Tauc(i,j))*anglec
#ifdef WET_DRY
          cff2=0.75_r8*0.5_r8*(z_w(i-1,j,1)+z_w(i,j,1)-                 &
     &                         z_w(i-1,j,0)-z_w(i,j,0))
          bustr(i,j)=SIGN(1.0_r8,bustr(i,j))*MIN(ABS(bustr(i,j)),       &
     &               ABS(u(i,j,1,nrhs))*cff2/dt(ng))
#endif
```

So defining `LIMIT_BSTRESS` by itself, as a Rutgers ROMS user would, did
nothing, and switching `WET_DRY` off removed the cap.

## The fix

The 13 `#ifdef WET_DRY` lines that guard the cap become
`#ifdef LIMIT_BSTRESS`:

| File | Blocks | Bottom-stress scheme |
|---|---|---|
| `BBL/ssw_bbl.h` | 2 (u and v) | `SSW_BBL` |
| `BBL/sg_bbl.h` | 2 | `SG_BBL` |
| `BBL/mb_bbl.h` | 2 | `MB_BBL` |
| `set_vbc.F` | 7: the factor `cff = 0.75/dt`, and u and v blocks for `UV_LOGDRAG`, `UV_QDRAG`, `UV_LDRAG` | drag laws without a BBL model |

```fortran
          bustr(i,j)=0.5_r8*(Tauc(i-1,j)+Tauc(i,j))*anglec
-#ifdef WET_DRY
+#ifdef LIMIT_BSTRESS
           cff2=0.75_r8*0.5_r8*(z_w(i-1,j,1)+z_w(i,j,1)-                 &
```

Because `WET_DRY` still defines `LIMIT_BSTRESS`, every build with `WET_DRY`
compiles to exactly the same Fortran as before, and builds with neither are
unchanged too. What is new: `-WET_DRY +LIMIT_BSTRESS` in a case header (or in
the build argument `CPP_OPTIONS`) gives the cap alone.

## When it matters

A case with shallow water that never dries (the shallowest water stays above
the drying threshold `DCRIT`): wetting and drying is not needed, but turning
`WET_DRY` off as shipped also removes the cap, which can turn a stable run into
an unstable one. In shallow reef cases with a few tens of centimetres of water
over the crest, the cap can bind in a large share of the cells shallower than
1 m, so it does real work there. Where it binds, the friction is set by the
layer thickness and the time step rather than the roughness: check how often
it binds before trusting the bottom stress in very shallow water (and see
`3-experimental/roms-bstress-implicit.patch`, an implicit bottom stress that
needs no cap).

## How the test works

The change is in which preprocessor option guards the code, so the test is
done at compile time, exactly, without running the model.
`tests/fixes/roms-limit-bstress/run.sh` ([README](../../../../tests/fixes/roms-limit-bstress/README.md))
builds COAWST's Veg_test (`SSW_BBL`, `WET_DRY` on) up to the compile stage,
before and after the patch, as shipped and with
`CPP_OPTIONS="-WET_DRY +LIMIT_BSTRESS"`, and compares the preprocessed
Fortran that ROMS compiles (`Build_roms/*.f90`):

1. Patched source: the 13 cap blocks test `LIMIT_BSTRESS`.
2. As shipped (`WET_DRY`): preprocessed Fortran before and after identical,
   all 405 files.
3. `-WET_DRY +LIMIT_BSTRESS`: no cap in the compiled code before the patch,
   the cap present after it; only the bottom-stress file differs.

## Engine test results

Run 2026-10-30 on the control VM (COAWST 26e6fb7; "before" is the series up to
this patch, `roms-sed-morph-tiling` and `roms-wec-stokes-fixes`). PASS:

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
