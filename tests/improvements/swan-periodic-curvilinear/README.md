# Test: swan-periodic-curvilinear

Checks [`2-improvements/swan-periodic-curvilinear.patch`](../../../build/coawst/patches/2-improvements/swan-periodic-curvilinear.md):
SWAN runs on periodic (`REPEATING`) curvilinear grids, the seam behaves like
any interior mesh, and nothing else changes.

## The idea

There is no exact solution to compare with, so the test uses symmetries a
correct periodic grid must have:

- **the same grid two ways**: a uniform grid given to SWAN as curvilinear
  must give exactly what the regular grid gives (the curvilinear code path
  against the old regular one);
- **moving the seam**: the reef rolled by half a period, so the seam runs
  through the pass where the waves change most, must give the same waves
  shifted back. A geometry error across the seam would show as 0.1-1 m;
- **a reef without a pass**: every column the same, including those at the
  seam;
- **processes**: 4 SWAN processes must give what 1 gives;
- **output anywhere**: `FRAME` and `POINTS` output across the seam and whole
  periods away must be found and equal the grid output there.

## What it does, step by step

1. **Builds** the standalone SWAN test case (`tests/cases/Swan_Periodic_Test`)
   before and after the patch (all fixes in both).
2. **Writes** 12 input folders (`make_inputs.py`): an A15-like reef (the
   cross-shore profile of `Reef_Ideal_A15`, a 200 m pass), waves Hs 1 m,
   Tp 10 s from 20 deg east of north, 1 h:

   | Case | Grid |
   |---|---|
   | `uni-reg-mid`, `uni-crv-mid` | uniform 20 m, 2 km period: regular, and the same as curvilinear |
   | `uni-reg-flat` | uniform, regular, no pass, `FORCE` output |
   | `str-mid` | stretched like A15: alongshore 20 m at the pass to 40 m (3 km period), A15's cross-shore rows |
   | `str-seam` | `str-mid` rolled by half a period: seam through the pass |
   | `str-flat` | stretched, no pass, `FORCE` output |
   | `str-norep` | `str-mid` without `REPEATING` |
   | `str-search` | `str-mid` with a `FRAME` over two periods and 9 `POINTS` (in the seam mesh, 1 and 2 periods away) |
   | `str-badper` | coordinate file whose last column is not column 1 shifted by a period |
   | `a15-mid`, `a15-seam`, `a15-norep` | `Reef_Ideal_A15`'s own SWAN grid and bathymetry (202 x 111) |

3. **Runs** (Docker, on this machine): all 12 with the patch on 1 process,
   4 at a time; `str-mid`, `str-seam`, `str-flat`, `a15-mid`, `a15-seam`
   also on 4 processes; without the patch, `str-mid` and the three cases
   that do not need the patch (`uni-reg-mid`, `uni-reg-flat`, `str-norep`).
4. **Checks** (`check.py`, last output at 1 h), each ok or BAD:
   - *refused before*: stock SWAN stops on `str-mid`;
   - *same grid*: `uni-crv-mid` = `uni-reg-mid` (Hs, Dir, dissipation);
   - *shift*: `str-seam` vs `str-mid` rolled back, below 1e-4 m; `a15-seam`
     vs `a15-mid`, below 5e-4 m; on 1 and 4 processes;
   - *processes*: Hs on 4 processes = 1, bit for bit; `FORCE` equal where
     both have values (stock SWAN leaves out the rows at the strip
     boundaries with several processes; see the patch document);
   - *periodic*: non-periodic differs from periodic by more than 0.1 m;
   - *flat reef*: Hs range along a row below 1e-4 m (uniform) and 5e-3 m
     (stretched: the effect of the varying spacing, not of the seam);
   - *search*: `FRAME` none missing, the second period equal to the first,
     in the seam mesh within 1e-5 m of the bilinear interpolation of the grid
     output; `POINTS` all found, copies equal, within the table's 3 decimals;
   - *bad period*: SWAN stops with the message;
   - *unchanged*: without vs with the patch, `uni-reg-mid`, `str-norep`,
     `uni-reg-flat` identical; `FORCE` on `uni-reg-flat` differs only in the
     seam columns.
5. **Plots** (`plot.py`) the figure in the patch document.

## Running it

```bash
PYTHON=~/venv/bin/python tests/improvements/swan-periodic-curvilinear/run.sh OUTDIR
```

About 20 min on 4 vCPUs. Needs Docker and Python with numpy, netCDF4 and
matplotlib.

## Reading the output

```
ok  shift str np4: seam through the pass vs rolled: max |dHs| 2.7e-05 m (limit 1e-04)
```

The reef with the seam through the pass gives, after shifting back, the same
waves within 2.7e-5 m: SWAN's iteration error where its sweeps meet the
seam.

## Last result

2026-10-31, control VM: PASS. Curvilinear = regular bit for bit; seam
through the pass 2.7e-5 m (stretched), 1.3e-4 m (A15 grid); 4 processes = 1;
non-periodic differs by 1.2 m; output search across the seam within 6.7e-7 m;
cases that do not need the patch unchanged.
