# Test: swan-closed-ring

Checks [`2-improvements/swan-closed-ring.patch`](../../../build/coawst/patches/2-improvements/swan-closed-ring.md):
coupled ROMS + SWAN on a grid that goes round an island and closes on itself
(an O-grid). The case is
[`tests/cases/Circle_Island`](../../cases/Circle_Island/README.md): a round
island with a fringing reef, 216 columns round the island, 80 rings
outwards.

## The idea

- Stock SWAN refuses a closed grid; the patch must make it run.
- The patch's main part is the coupler's index map: which SWAN value goes
  to which ROMS point and back. A wrong map can still run, and can even
  look plausible, so the test compares the exchanged fields directly at
  every output time: ROMS's `Hwave` against SWAN's Hs (they must be
  identical, also in ROMS's two copy columns at the seam), and SWAN's water
  level against ROMS's zeta. It does so with 1, 2 and 3 SWAN processes,
  because each process holds its own strip of rings and the map is built per
  strip.
- Results must not depend on how the work is split (ROMS tiles, SWAN
  processes), nor much on where the seam is. Moving the seam changes where
  SWAN's sweeps start, so the result is not exact there; the test compares
  that change with what SWAN's own iteration count does to the solution.
- With waves aimed straight inward all round the island, the solution should
  repeat every 10 degrees (6 columns = one SWAN direction bin), at the seam as
  elsewhere.
- Grids that do not close must be unchanged: Reef_Ideal_A15 before and
  after the patch, bit for bit.

## What it does, step by step

1. **Builds** Circle_Island and Reef_Ideal_A15, each before and after the
   patch (`tests/tools/build_pair.sh`; the series up to, and up to and
   including, `swan-closed-ring`).
2. **Runs**, 60 min each, output every 10 min (the coupling interval):

   | Folder | Image | Layout | What |
   |---|---|---|---|
   | `before` | before | ROMS 6x1 + 2 SWAN | waves from the north |
   | `north` | after | 6x1 + 2 | waves from the north (reference) |
   | `north-1x6-1swan` | after | 1x6 + 1 | other layout |
   | `north-2x2-3swan` | after | 2x2 + 3 | other layout |
   | `north-roll54` | after | 6x1 + 2 | seam moved 54 columns (90 degrees, to east) |
   | `north-it5`, `north-roll54-it5` | after | 6x1 + 2 | the two above with 5 SWAN iterations per time step |
   | `inward` | after | 6x1 + 2 | waves aimed inward all round |
   | `a15-before`, `a15-after` | A15 before/after | 1x6 + 2 | a periodic grid that does not close |
   | `restart/` | after | 6x1 + 2 | 60 min straight, 30 + 30 min restarted |

   The variants are sed scripts on the case's inputs (see the case README).
3. **Checks** (`check.py`), each PASS or FAIL:
   - *refused*: before the patch SWAN stops with "no period found";
   - *finished*: every run after the patch finished, no NaN;
   - *coupler*: `Hwave` = SWAN Hs (also ROMS columns 0 and Lm+1), and SWAN's
     water level = ROMS's zeta of the previous exchange within 2e-4 m, at
     every output time after the first, in every run;
   - *seam*: the jump across the seam is no larger (beyond 1e-3 of the
     field's size) than between other neighbouring columns nearby;
   - *seam_shift*: moving the seam changes each field by less than half of
     what 5 SWAN iterations per step instead of 1 change it;
   - *processes*: the other layouts equal the reference (within 1e-6);
   - *symmetry*: with inward waves, Hs turned by 6 columns differs by less
     than 1 % of Hs, and no more near the seam than far from it (factor 1.5);
   - *unchanged*: A15 before = after, bit for bit;
   - *restart*: 30 + 30 min restarted equals 60 min straight (within 1e-8).

   `plot.py` draws the document's figure.

## Running it

```bash
PYTHON=~/venv/bin/python tests/improvements/swan-closed-ring/run.sh OUTDIR
```

About 20 min to build four images and 1.2 h of runs on 4 vCPUs (8 processes
on 4 vCPUs need `--oversubscribe`, which `run.sh` sets). With `STAGES=build`
the runs can be made elsewhere (each 2-4 min on an 8-vCPU machine, 10 min
with 5 SWAN iterations) into the folder layout above, then `STAGES=check`.

## Last result

2026-10-31: PASS. Runs on Cloud Batch (c2d-standard-8 Spot), `before` on the
control VM.

| Check | Result |
|---|---|
| refused | "REPeating curvilinear grid: no period found" |
| coupler | Hs to ROMS identical in all runs; zeta to SWAN within 1.1e-4 m (1.5e-4 inward); one ring off would be 2.3e-2 m |
| processes | identical (u, v within 1e-11 relative) |
| seam | at most 6e-4 of the field size beyond the neighbours' jumps |
| seam_shift | at most 0.28 of SWAN's 1-vs-5-iteration difference (0.3 mm sea level, 6 mm Hs, 2 cm/s radial current, on the crest beside the seams) |
| symmetry | Hs repeats every 10 degrees within 8.6e-3 m (0.55 %), near the seam 7.4e-3, far 8.0e-3 m |
| unchanged | A15 bit-identical |
| restart | 1e-11 relative (zeta, currents, AKv, tke, SWAN Hs bit-identical), after the case's `DSTART` was set (see below) |

Details and the figure in the patch document. The runs were made with the
case's grid file before a correction of its u- and psi-point coordinates
(they were one column off); ROMS does not use those coordinates in this
case, and every other input is bit-identical. They were also made before the
case's `DSTART` was set; that changes only restarted runs (a fresh run is
bit-identical either way), and the restart run is the one made after it.
