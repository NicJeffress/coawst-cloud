# Test: roms-diag-implicit-drag

Checks [`3-experimental/roms-diag-implicit-drag.patch`](../../../build/coawst/patches/3-experimental/roms-diag-implicit-drag.md):
with implicit bottom stress and canopy drag, the momentum budget in
`ocean_dia.nc` must close, and the solution must not change.

## What it does

Reef_Ideal_A15_veg at DT 3 s, NDTFAST 12, 15 levels, density-1 canopy, 2 h, with
`Dout(M2fveg)` and `Dout(M3fveg)` on in `vegetation.in`. `closure.py` subtracts
the acceleration from the sum of every term in the file, 2-D and 3-D, leaving out
only the terms that are parts of another (`xadv`, `yadv`, `xvisc`, `yvisc`, and
`zeta`, `zetaw`, `zqsp`, `zbeh`, which add up to `prsgrd`). A missing or garbage term shows up as a residual. There is no `run.sh` yet: these runs need
16 processes, so they were run on Cloud Batch.

```bash
python -I tests/experimental/roms-diag-implicit-drag/closure.py ocean_dia.nc
```

## Last result (2026-11-04)

Largest residual over 2 h, against the largest term (hourly averages):

| Kernel | `ubar` | `vbar` | `u` | `v` |
|---|---|---|---|---|
| AB3-AM4 | 6.6e-10 of 1.1e-2 | 1.8e-9 of 3.0e-2 | 2.2e-9 of 4.4e-2 | 8.6e-9 of 8.8e-2 |
| LF-AM3 | 5.5e-10 of 1.1e-2 | 2.0e-9 of 3.0e-2 | 2.8e-9 of 4.4e-2 | 8.2e-9 of 8.8e-2 |

About 1e-7 of the largest term: single-precision output. With AB3-AM4, every
history variable in every record was bit-identical to a build without the patch
(121 records). The LF-AM3 solution was not compared; the changes there are
to diagnostic arrays only. Before the patch, on a bare reef, `vbar_bstr` integrated
across the reef was 0.001 where the leftover in the budget was 0.60 m³/s² per
metre alongshore.
