# roms-prsgrd40-wetdry.patch: the PJ_GRADP pressure gradient compiles with WET_DRY

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no: a compile fix. Builds that failed now compile; every other build is unchanged (identical executables) |
| **Default** | on (only compiled with `PJ_GRADP`) |
| **Files** | `ROMS/Nonlinear/prsgrd40.h` (two declaration blocks) |
| **Evidence** | Reef_Ideal_A15 with `PJ_GRADP` and `WET_DRY`: compile error before, compiles and runs after; with `PJ_GRADP` alone, identical executables before and after |
| **Test** | [`tests/fixes/roms-prsgrd40-wetdry/run.sh`](../../../../tests/fixes/roms-prsgrd40-wetdry/run.sh), see its [README](../../../../tests/fixes/roms-prsgrd40-wetdry/README.md) |
| **Upstream** | not yet reported to COAWST |

## In short

ROMS offers several schemes for the horizontal pressure gradient. One of
them, `PJ_GRADP`, cannot be compiled together with wetting and drying
(`WET_DRY`) in COAWST v3.9. Its routine receives the wet/dry masks and uses
them, but never declares them, so gfortran stops with "Symbol 'umask_wet' has
no IMPLICIT type". The patch adds the two missing declarations, written as in
the other pressure-gradient routines.

## Background: pressure-gradient schemes in ROMS

In terrain-following (sigma) coordinates the horizontal pressure gradient is
the difference of two large terms over sloping levels, and its truncation
error drives spurious currents over steep topography. ROMS has several
schemes, chosen by a cpp option; `ROMS/Nonlinear/prsgrd.F` includes one file:

| Option | File | Scheme |
|---|---|---|
| (none) | `prsgrd31.h` | standard density Jacobian |
| `DJ_GRADPS` | `prsgrd32.h` | density Jacobian with monotonized cubic fits (Shchepetkin & McWilliams 2003); the same scheme as UCLA ROMS |
| `PJ_GRADP` | `prsgrd40.h` | finite-volume pressure Jacobian (Lin 1997): pressure integrated around each cell's faces |
| `PJ_GRADPQ2`, `PJ_GRADPQ4` | `prsgrd42.h`, `prsgrd44.h` | pressure Jacobian with quartic reconstruction of density (Shchepetkin & McWilliams 2003) |

No scheme is best everywhere; the usual advice is to test the candidates on
the grid in question with a run at rest, where every current is error.

**This project's own cases use `DJ_GRADPS`.** In a 12-hour test at rest with
stratification (N² = 1e-4) on a realistic reef grid with steep slopes, the
largest spurious currents were 24 mm/s with `DJ_GRADPS`, 175 mm/s with
`PJ_GRADPQ4` and 740 mm/s with `PJ_GRADP` (wrong from the first step). This
fix is therefore for other users who choose `PJ_GRADP`, not a
recommendation of it.

## The bug

`prsgrd40.h` has the usual two parts: `prsgrd`, which calls the tile routine
`prsgrd40_tile` with the grid arrays, and the tile routine, which does the
work. With `WET_DRY` the call passes the wet/dry masks:

```fortran
      CALL prsgrd40_tile (ng, tile,                                     &
     &                    LBi, UBi, LBj, UBj,                           &
     &                    IminS, ImaxS, JminS, JmaxS,                   &
     &                    nrhs(ng),                                     &
#ifdef WET_DRY
     &                    GRID(ng)%umask_wet,                           &
     &                    GRID(ng)%vmask_wet,                           &
#endif
```

and the tile routine lists them in its arguments and multiplies the
pressure-gradient terms by them, so no force acts across a dry face:

```fortran
#ifdef WET_DRY
              ru(i,j,k,nrhs)=ru(i,j,k,nrhs)*umask_wet(i,j)
#endif
```

but its declarations (one block for `ASSUMED_SHAPE` arrays, one for explicit
bounds) do not include `umask_wet` and `vmask_wet`. ROMS compiles with
`IMPLICIT NONE`, so the build stops:

```
Error: Symbol 'umask_wet' at (1) has no IMPLICIT type
Error: Symbol 'vmask_wet' at (1) has no IMPLICIT type
```

The other schemes (`prsgrd31.h`, `prsgrd32.h`, `prsgrd42.h`, `prsgrd44.h`)
declare them, so only `PJ_GRADP` is affected.

## The fix

The two declarations, in both blocks, as in `prsgrd32.h`:

```fortran
 #ifdef ASSUMED_SHAPE
+# ifdef WET_DRY
+      real(r8), intent(in) :: umask_wet(LBi:,LBj:)
+      real(r8), intent(in) :: vmask_wet(LBi:,LBj:)
+# endif
       real(r8), intent(in) :: om_v(LBi:,LBj:)
 ...
 #else
+# ifdef WET_DRY
+      real(r8), intent(in) :: umask_wet(LBi:UBi,LBj:UBj)
+      real(r8), intent(in) :: vmask_wet(LBi:UBi,LBj:UBj)
+# endif
       real(r8), intent(in) :: om_v(LBi:UBi,LBj:UBj)
```

Nothing else changes: the arguments were already passed and used.

## When it matters

Only for builds with both `PJ_GRADP` and `WET_DRY`, which could not be built
before. All other builds compile to the same executable.

## How the test works

[`tests/fixes/roms-prsgrd40-wetdry/run.sh`](../../../../tests/fixes/roms-prsgrd40-wetdry/run.sh)
builds the idealized reef case (`tests/cases/Reef_Ideal_A15`) with
`CPP_OPTIONS="-DJ_GRADPS +PJ_GRADP"`, before and after the patch:

- with `+WET_DRY`: before must stop on the undeclared masks; after must
  compile, and run to the end with finite fields;
- without `WET_DRY`: the executables before and after must be identical.

## Results

Run 2026-11-02 on the control VM (4 vCPUs), engine build settings,
Reef_Ideal_A15 with `-DJ_GRADPS +PJ_GRADP`:

| Check | Result |
|---|---|
| `+WET_DRY`, before the patch | does not compile: `'umask_wet'`, `'vmask_wet'` have no IMPLICIT type |
| `+WET_DRY`, with the patch | compiles |
| without `WET_DRY`, before vs after | identical `coawstM` (md5 `80d40907...`) |
| `+WET_DRY` with the patch, 30 min, ROMS 1x2 + 2 SWAN | runs to the end (154 s), 4 history records, all fields finite, largest current 0.30 m/s |

**PASS.**

## Limits

- The test shows that the build compiles and runs. It does not assess
  `PJ_GRADP`'s accuracy, which depends on the grid and stratification (see
  above).
- The reef case never dries (shallowest water 0.35 m at low tide against a
  drying threshold of 0.10 m), so the masks are 1 everywhere in the run.
  The masking itself is upstream's code and is unchanged.
