# Test: swan-vegetation-fixes

Checks [`1-fixes/swan-vegetation-fixes.patch`](../../../build/coawst/patches/1-fixes/swan-vegetation-fixes.md):
COAWST's vegetation routine in SWAN (`VEGETATION 3`) and SWAN's own plant input.

## The idea

Two kinds of check. Two of the five changes are about formulas and grid
numbers in the source, which are checked by reading the source. The other
three show up when COAWST's own vegetation example is run with SWAN's
COAWST vegetation routine switched on: stock SWAN cannot even start it, and
the patched one must write the drag coefficient it uses, including where the
plants reach the surface.

## What it does, step by step

1. **Source check** (`check_source.py`) on the SWAN source with the patch
   series before and after this patch:
   - `veg3_flexible_plants`: the second moment of area is
     `diameter x thickness^3 / 12` and the Cauchy number is not divided by an
     extra 1e12, as in ROMS's `vegetation_drag.F`;
   - `plant_input_grids`: plant height, diameter and thickness are
     interpolated on the input grids that `INPGRID` registers for them (18, 19,
     20), and `INPGRID NPHT` sets the flag `VARNPH`.
   It also prints a note about what is known and left unchanged (the
   unstructured-grid branch tests the wrong grid types).
2. **Builds** COAWST's **Veg_test** (ROMS + SWAN with `VEG_SWAN_COUPLING`:
   ROMS sends its plant fields to SWAN) before and after the patch, with SWAN
   bounds-checked (`-fcheck=bounds`).
3. **Runs**, 10 min each, with SWAN's `VEGETATION 1` changed to
   `VEGETATION 3` (COAWST's routine, drag method 1: Cd = 1) and output of the
   drag coefficient (`DICD`) and depth every 5 min:
   - `submerged`: the case's plants, 0.3 m tall in 1 m of water;
   - `emergent`: the same with 1.5 m plants (the test edits a copy of the
     initial file), so every plant sticks out of the water.
4. **Checks**:

   | Run | Expected |
   |---|---|
   | submerged-before, emergent-before | stop at once: `array 'vegyml' above upper bound of 0` (`veg3_young_modulus`) |
   | submerged-after, emergent-after | run; `DICD` written, not all zero (`dicd_output`) |
   | emergent-after | Cd = 1 (drag method 1) at every emergent plant, not 1.95 (`veg3_emergent_cd`) |

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/swan-vegetation-fixes/run.sh COAWST-<ref>.tar.gz OUTDIR
```

About 25 min on 4 vCPUs. Needs Python with numpy, scipy (for the `.mat`
output) and netCDF4.

## Reading the output

```
veg3_flexible_plants  second moment of area = D t^3/12   VEGDIL_LOC*VEGTHK_LOC**(3./12.) BAD   (before)
...
   submerged-before: stops, VEGYML never allocated (veg3_young_modulus)   ok
dicd_output           DICD written, submerged plants     values [1.0]                     ok
veg3_emergent_cd      Cd at emergent plants = 1 (drag method 1)  100 points, Cd [1.0]     ok
PASS
```

## Last result

2026-10-30, control VM: PASS.
