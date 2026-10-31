# Test: roms-limit-bstress

Checks [`1-fixes/roms-limit-bstress.patch`](../../../build/coawst/patches/1-fixes/roms-limit-bstress.md):
the bottom-stress cap must be switched by `LIMIT_BSTRESS`, not by `WET_DRY`.

## The idea

The patch changes which preprocessor option guards 13 blocks of code. That
can be tested exactly without running the model: look at the Fortran that
the compiler actually receives (after the C preprocessor has removed the
blocks that are switched off) and check that the cap is there when, and only
when, it should be.

## What it does, step by step

1. Builds COAWST's stock **Veg_test** (it uses the `SSW_BBL` bottom boundary
   layer and has `WET_DRY` on) up to the compile stage (`docker build
   --target build`), four times: before and after the patch, each as shipped
   and with `CPP_OPTIONS="-WET_DRY +LIMIT_BSTRESS"` (the cap without wetting
   and drying).
2. Copies the preprocessed Fortran (`/opt/COAWST/Build_roms/*.f90`) out of
   each image.
3. Checks:
   1. in the patched source, 13 blocks test `LIMIT_BSTRESS`;
   2. as shipped, before and after give identical preprocessed Fortran (the
      patch changes nothing for builds with `WET_DRY`);
   3. with `-WET_DRY +LIMIT_BSTRESS`, the cap (`MIN(ABS(bustr...))`) is absent
      before the patch and present after it, and only the bottom-stress file
      differs.

## Running it

```bash
tests/fixes/roms-limit-bstress/run.sh OUTDIR
```

About 15 min on 4 vCPUs (four builds). Needs only Docker.

## Reading the output

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

"2 limiter lines" are the u and v caps of `SSW_BBL`, compiled into
`bbl.f90`.

## Last result

2026-10-30, control VM: PASS.
