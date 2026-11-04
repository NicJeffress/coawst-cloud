# Test: swan-bkd-exact-restart

Checks [`1-fixes/swan-bkd-exact-restart.patch`](../../../build/coawst/patches/1-fixes/swan-bkd-exact-restart.md):
a coupled run with `BREAKING BKD` restarted from `RESTART ... UNFormatted`
files must continue exactly as if it had never stopped.

## What it does

Reef_Ideal_A15_veg at DT 3 s, NDTFAST 12, 15 levels, on `c2d-standard-16` with
10 ROMS + 6 SWAN processes, history every minute. A straight run, and the same
run in 1 h segments; `compare.py` compares every history variable record by
record. There is no `run.sh` yet: these runs need 16 processes, so they were
run on Cloud Batch.

```bash
python -I tests/fixes/swan-bkd-exact-restart/compare.py STRAIGHT/ocean_his.nc SEG_002/ocean_his.nc
```

## Last result (2026-11-04, canopy density 1 and bare reef)

| Variant, restart at 1 h, 2 h run | From the first SWAN exchange after the restart |
|---|---|
| before, `BKD` (with or without triads; `GLS_Kmin` 1e-8 or 7.6e-6) | differs: u 3.6e-12 m/s at 71 min, 1e-7 m/s at 2 h in the first variant; 5e-5 m/s after 3 h in a 4 h segment |
| before, `CON 1.0 0.73` | bit-identical in the 16 fields compared |
| after, `BKD`, canopy and bare | bit-identical in every history variable, every record after the restart |
| after, `BKD`, 3 segments of 1 h, canopy | bit-identical at the end of each segment |

The first history record of a restarted segment still differs in fields ROMS
computes for output: `w`, `zetaw`, `qsp`, `bernoulli_head`, `u_wec_stress`,
`v_wec_stress` (up to 5.5 in the stress variables). They agree from the next
record on; a merge should keep the previous segment's copy of that record. In
the restart file only `ru` and `rv` differ, in the periodic ghost columns.
