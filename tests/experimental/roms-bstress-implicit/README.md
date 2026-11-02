# Test: roms-bstress-implicit

Records what [`3-experimental/roms-bstress-implicit.patch`](../../../build/coawst/patches/3-experimental/roms-bstress-implicit.md)
(option `BSTRESS_IMPLICIT`) does on the idealized cases: `run.sh` on the
cases as they are (a record, not an accuracy test), `thin_crest.sh` on
thin-crest variants of Reef_Ideal_A15, where the cap the option replaces
binds. (Options off: [`options-off`](../options-off/README.md).)

## What it does, step by step

1. **Builds**, all with `-SPLINES_VVISC` (the option needs the tridiagonal
   vertical-viscosity solver), Reef_Ideal_A15 without and with the option,
   and Circle_Island with `+LIMIT_BSTRESS` (the cap the option replaces) and
   with the option.
2. **Runs** each for 1 h.
3. **Checks** (`check.py`): whether each run finished; differences in
   depth-mean current, sea level and Hs; the largest bottom stress. PASS if
   the two A15 runs finished.

## Running it

```bash
PYTHON=~/venv/bin/python tests/experimental/roms-bstress-implicit/run.sh OUTDIR
```

## Last result

2026-11-01: PASS (as a record), runs on Cloud Batch. All four runs finished.
A15 explicit vs implicit: currents within 4.6 cm/s at 99.9 % of cells
(largest 7.0 cm/s), bottom stress (99.9th pct) 6.23 vs 6.25 N m⁻². Circle
capped vs implicit: within 4.7 cm/s (largest 5.1), 1.30 vs 1.29 N m⁻². The
failure on the realistic case is not reproduced here.

## Thin-crest variants: `thin_crest.sh`

```bash
PYTHON=~/venv/bin/python tests/experimental/roms-bstress-implicit/thin_crest.sh OUTDIR [MINUTES] [GRIDS]
```

1. **Writes** `OUTDIR/Reef_Ideal_A15_thin` with `make_thin_crest.py`: the A15
   case plus three grids (ROMS grid and SWAN bathymetry; only the reef
   columns change): `thin_smooth` (crest 0.30 m, flanks eased to rx0 <= 0.32),
   `thin_steep` (crest 0.30 m over two rows, 0.71 m either side, rx0 0.41)
   and `steep_050` (crest 0.50 m over two rows, 1.19 m either side).
2. **Builds** three images, all with `-SPLINES_VVISC`: `cap`
   (+LIMIT_BSTRESS), `nocap` (the explicit stress as shipped) and `imp`
   (+BSTRESS_IMPLICIT).
3. **Runs** each on each grid in GRIDS (default `thin_steep`; `"default_1
   thin_smooth thin_steep steep_050"` for all) for MINUTES (default 180,
   through low tide), ROMS 1x6 + 2 SWAN, history every 10 min.
4. **Summarizes** (`thin_crest_summary.py`: fastest current, vertical
   Courant number, crest current, lagoon set-up per record; `cap_stats.py`:
   the stress stability number S = tau DT / (Hz_1 |u_1|) on the crest, which
   `LIMIT_BSTRESS` holds at 0.75). No pass/fail: it is a comparison.

### Last result

2026-11-02, all four grids, on Cloud Batch (c2d-standard-8 Spot): all twelve
runs finished. The option and the uncapped explicit stress agree to 1 % in
crest current and set-up on every grid; the capped stress gives 40-75 %
faster crest flow on the 0.30 m crests (the cap binds at 51-67 % of the
crest cells and halves the effective drag). The uncapped explicit stress ran
stably at S up to 7-11 (median 1.4-1.9). With Hs ramped to 2 m (a
`wavebc_north_2m.txt` added to the case, `SWANSED` pointing `BOUNDPAR2` at
it) the capped runs changed by 15 % in set-up between DT 6 and 3 s, the
others by 0.1 %. Full tables in the patch document.
