# roms-ts-fixed-density.patch: with TS_FIXED a restart was not exact

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | builds with `TS_FIXED` only, at round-off: the density fields now follow the free surface; restarts become bit-identical. Builds without `TS_FIXED`: unchanged |
| **Default** | on |
| **Files** | `ROMS/Nonlinear/main3d.F` |
| **Evidence** | idealized canopy reef with `TS_FIXED`, 60 min straight against 30 + 30 min restarted, double-precision restart records: before, u differs at 443 050 points (up to 5.4e-14 m/s), after bit-identical; without `TS_FIXED` bit-identical history |
| **Test** | [`tests/fixes/roms-ts-fixed-density/run.sh`](../../../../tests/fixes/roms-ts-fixed-density/run.sh), see its [README](../../../../tests/fixes/roms-ts-fixed-density/README.md) |
| **Upstream** | not reported yet |

## In short

`TS_FIXED` keeps temperature and salinity fixed. `main3d.F` then skips
`rho_eos` at every step, so the density, the buoyancy frequency and the depth
averages of the density that the barotropic pressure gradient uses (`rhoA`,
`rhoS`) are computed once, during initialization, from the layer depths of
that moment. Those depths move with the free surface, so a run restarted at
time t computes them with the free surface of t, while the uninterrupted run
still uses those of its start. With a uniform density the difference is in
the last bits, but it enters the first barotropic step after the restart and
grows: on the idealized reef 1e-16 relative after one step, 3.7e-7 m/s after
four hours. The patch calls `rho_eos` every step with `TS_FIXED` as well.

## How it was found

A segmented 24 h canopy run (4 h segments) differed from the straight run by
3.7e-7 m/s at hour 8, against the round-off of the other restart tests. A
debug build wrote bit-exact checksums of about 60 arrays after every phase of
the step and every barotropic fast step, for 100 steps after a restart, in
both runs. After the restart read the state was exact (the masked boundary
row of u is read as +0 where the straight run held -0, which is equal); after
the 3-D right-hand side everything except the barotropic averages matched;
the first array to differ inside the first fast step was `rhoA`/`rhoS`, and
they differed already at the start of the step: the straight run still had
them from its initialization at t = 0. (The AB3-AM4 kernel's fourth time level,
which the restart file does not hold, also differs, but it is not read before
it is written.) With `rho_eos` called every step the restarted run is
bit-identical from its first barotropic step through step 405, a wave exchange
included.

## The change

```fortran
!  coawst-cloud patch roms-ts-fixed-density: also with TS_FIXED. ...
                CALL rho_eos (ng, tile, iNLM)
```

in place of the `# ifndef TS_FIXED` block around that call, and the
`USE rho_eos_mod` without the guard. `rho_eos` costs one pass over the 3-D
grid per step.

## Test results

`tests/fixes/roms-ts-fixed-density/run.sh` (2026-11-03), tests/cases/Reef_Ideal_A15_veg
(`TS_FIXED`), ROMS 1 x 2 + 2 SWAN, 60 min straight against 30 + 30 min, the
restart records at 60 min (double precision):

| | u | v | ubar | vbar | zeta |
|---|---|---|---|---|---|
| before | 5.4e-14 (443 050 points) | 1.5e-14 | 7.5e-16 | 9.4e-16 | 9.7e-16 |
| after | **0** | **0** | **0** | **0** | **0** |

Builds without `TS_FIXED` (tests/cases/Reef_Ideal_A15 with `-TS_FIXED`, 10 min,
history every 2 min): bit-identical.

## Who is affected

Every `TS_FIXED` run that is restarted (segmented runs on interruptible
machines), at round-off level that then grows; and every `TS_FIXED` run whose
free surface moves far from its initial state, whose barotropic pressure
gradient used the start-time densities throughout (immaterial with uniform
density, as in the A15 canopy and bare cases).
