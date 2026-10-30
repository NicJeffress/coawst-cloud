# swan-vegetation-fixes.patch: COAWST's vegetation routine in SWAN, and SWAN's plant input

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | yes, for SWAN with `VEGETATION 3` (it could not run correctly before) and for flexible plants in it; output only for item 17; standalone SWAN, or coupled without `VEG_SWAN_COUPLING`, with spatially varying plant input (item 10) |
| **Default** | on |
| **Files** | `SWAN/src/swanpre1.ftn` (items 8, 10), `SWAN/src/swancom2.ftn` (9, 16), `SWAN/src/swanmain.ftn` (10), `SWAN/src/swanout1.ftn` (17) |
| **Evidence** | Veg_test with `VEGETATION 3`: stock stops at once, patched runs and writes the drag coefficient, also for emergent plants; source check of items 9 and 10 (results below) |
| **Test** | [`tests/fixes/swan-vegetation-fixes/run.sh`](../../../../tests/fixes/swan-vegetation-fixes/run.sh) |
| **Upstream** | same code in COAWST v3.8.1 and `main`; not reported (COAWST#211, odd results with `VEG_SWAN_COUPLING`, may be related to item 10) |

## Background: SWAN's vegetation options in COAWST v3.9

`VEGETATION iveg height diameter nstems drag` selects the vegetation model:

- `iveg 1`: SWAN's own (Dalrymple; Mendez and Losada), height and diameter
  from the command, density = nstems x the `NPLANTS` input grid;
- `iveg 2` (also `VEGCtation`): Jacobsen et al. (2019);
- `iveg 3`: COAWST's `SVEG_COAWST`, which takes density, height, diameter
  and thickness from the spatial fields ROMS sends with `VEG_SWAN_COUPLING`
  (what v3.7's `VEGCoawst` did). Here `drag` is a method switch: 1 = Cd 1,
  2 = Cd from the Keulegan-Carpenter number (Mendez and Losada; Suzuki).

`iveg 3` is the one that keeps SWAN's plants identical to ROMS's when they
vary in space. Items 8, 9, 16 and 17 are in it; item 10 is in SWAN's own
plant input.

## Item 8: VEGETATION 3 read an array that was never allocated

`SVEG_COAWST` reads Young's modulus `VEGYML(1)` (for flexible plants), but
only the `VEGCtation` command (which forces `iveg 2`) allocated `VEGYML`. So
`VEGETATION 3` read unallocated memory: a crash or a garbage stiffness,
depending on the machine. Fix: `VEGETATION` allocates it with a rigid
default, 1e9 Pa (the value of v3.7's `VEGCoawst` example), unless the command
already set it.

## Item 9: flexible plants in SVEG_COAWST were always rigid

The effective (bent) height of flexible plants comes from the Cauchy number,
the ratio of drag to stiffness (Luhar and Nepf). Two errors made it ~0, i.e.
every plant rigid:

```fortran
-            SMA        = VEGDIL_LOC*VEGTHK_LOC**(3./12.)
+            SMA        = VEGDIL_LOC*VEGTHK_LOC**3/12.
...
-            CAUCHY_NUM = MIN(CFF1/(CFF2+MAX_EPS), MAX_EPS)
+            CAUCHY_NUM = MIN(CFF1/CFF2, MAX_EPS)
```

The second moment of area was thickness to the power 0.25 (operator
precedence) instead of diameter x thickness^3 / 12, and the Cauchy number was
divided by 1e12 (`MAX_EPS`) added to the stiffness. ROMS's own
`vegetation_drag.F` (`VEG_FLEX`, same authors) uses `diam*thck**3/12` and
divides by `MAX(E*I, min_eps)` (the guard against zero stiffness stays in the
lines before). Rigid plants (large E) still have their full height, so cases
with coral-like rigid elements do not change; flexible plants (seagrass,
marsh) now bend.

## Item 10: plant height, diameter and thickness interpolated on the wrong input grids

`INPGRID`/`READINP` register spatially varying plant height, diameter and
thickness (`NPHT`, `NPDA`, `NPTK`) as SWAN input grids 18, 19 and 20, but
`SWRBC` (and the unstructured-grid branch) interpolated them with `SVALQI` on
grids 16, 17 and 18, which SWAN 41.51 uses for the sea-swell inputs
(`HSS`/`TSS`/`DSS`), undefined in such a run. The interpolation then used an
undefined grid geometry: garbage plant properties, or a crash at start-up
when the garbage pointed outside valid memory (seen once in 7 cloud runs;
Valgrind showed 4 reports of `SVALQI` branching on uninitialised values
before the fix, none after). Also `INPGRID NPHT` set the flag `VARNPL`
instead of `VARNPH`. Fix: grids 18, 19, 20 and `VARNPH`.

Who is affected: SWAN's own plant input path. In a coupled run with
`VEG_SWAN_COUPLING`, the coupler writes ROMS's plant fields into SWAN's arrays
at every exchange, and the first exchange comes after `SWRBC` and before the
first wave step, so wrong values never reached a coupled computation; the
coupled risk was the start-up crash. Standalone SWAN, or a coupled run
without `VEG_SWAN_COUPLING`, used the wrong values throughout.

## Item 16: plants that reach the surface got a fixed Cd of 1.95

For submerged plants `SVEG_COAWST` computes Cd with the drag method of the
command; for water shallower than the plants it used a fixed 1.95, and for
water exactly as deep as the plants no branch ran (no dissipation, Cd
undefined). SWAN's own `VEGETATION 1` keeps the given Cd for emergent plants,
and ROMS uses its `CD_VEG` everywhere, so the two models disagreed exactly
where plants matter most. In a reef case whose 0.4 m canopy reaches the
surface over a 0.5 m deep crest at low tide, the crest's wave dissipation
would nearly double at every low tide. Fix: emergent plants use the drag
method too, with the canopy filling the water column (method 2 takes the
orbital velocity at the surface, alpha = h/d = 1). With method 1 and constant
plant fields, `VEGETATION 3` now gives what `VEGETATION 1` gives (checked on
an A15 vegetation case). If 1.95 was meant as a separate Cd for emergent
plants, that would need a new parameter in both models.

## Item 17: the vegetation drag coefficient output was always zero

COAWST's block for writing `DICD` (SWAN quantity 201, the Cd that
`SVEG_COAWST` stores) tested and filled quantity 80, which SWAN 41.51 uses for
`REDC`. So `BLOCK ... DICD` wrote zeros. The Cd used in the computation was
not affected. Fix: quantity 201. (It is in this patch rather than with the
other output fixes because showing it needs `VEGETATION 3`, i.e. item 8.)

## Test

`tests/fixes/swan-vegetation-fixes/run.sh SOURCE OUTDIR`:

1. **Source check** (`check_source.py`): second moment of area and Cauchy
   number as in ROMS (item 9); plant fields interpolated on the grids
   `INPGRID` registers for them, and `VARNPH` (item 10).
2. **COAWST's Veg_test** (ROMS + SWAN, `VEG_SWAN_COUPLING`, 0.3 m plants in
   1 m of water) switched to `VEGETATION 3` (drag method 1), SWAN
   bounds-checked, 10 min, `DICD` and `DEPTH` written every 5 min; once as
   shipped (submerged plants) and once with 1.5 m plants (emergent, initial
   file edited by the test). Before: stops at once (item 8). After: runs,
   `DICD` is written (item 17), and Cd is 1.0 at the emergent plants (item 16).

## Engine test results

Run 2026-10-30 on the control VM; "before" is the series up to this patch,
"after" adds it. PASS:

```
== 1. source check
before: item 9   second moment of area = D t^3/12        VEGDIL_LOC*VEGTHK_LOC**(3./12.) BAD
        item 9   Cauchy number not divided by MAX_EPS    MIN(CFF1/(CFF2+MAX_EPS), ...  BAD
        item 10  NPHTF / NPDAF / NPTKF interpolated on grids 18 / 19 / 20:
                 SVALQI grids [16] / [17] / [18]                                       BAD
        item 10  INPGRID NPHT sets VARNPH                VARNPL                        BAD
after:  all six ok
== 2. Veg_test with VEGETATION 3 (SWAN -fcheck=bounds), 10 min
before: submerged and emergent both stop at once:
        Fortran runtime error: Index '1' of dimension 1 of array 'vegyml'
        above upper bound of 0                        (item 8)
after:  item 17  DICD written, submerged plants       values [1.0]   ok
        item 17  DICD written, emergent plants        values [1.0]   ok
        item 16  Cd at emergent plants = 1 (method 1)  100 points     ok
```

Veg_test's own run (submerged, 10 min, 1 ROMS + 1 SWAN) takes about 2.7 min
on the control VM.

## Limits

- Item 10, unstructured grids: the branch for unstructured SWAN grids still
  tests `IGTYPE(16)`, `IGTYPE(17)`, `IGTYPE(18)` (the grid types of the
  sea-swell grids) before reading plant height, diameter and thickness, which
  live on grids 18, 19, 20. Not changed (no unstructured case here); the test
  prints it as a note.
- In SWAN 41.51 grid 18 is also the sea-swell direction grid (`DSS`), so a
  case using both that and `NPHT` would collide. Not changed.
- Item 9 is checked in the source; a run with flexible plants in
  `VEGETATION 3` needs a way to set Young's modulus there (it takes the rigid
  default), so it is not run here.
