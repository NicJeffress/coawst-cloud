# roms-roller-substeps.patch: the Reniers roller blew up at ordinary time steps

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | yes, `ROLLER_RENIERS` only: the roller is stable at any DT; where its old single step was stable the answer changes only by the time-stepping of the roller itself. Builds without `ROLLER_RENIERS` are unchanged (the code is inside its `#ifdef`) |
| **Default** | on |
| **Files** | `ROMS/Nonlinear/WEC/wec_roller.F` (`wec_roller_tile`) |
| **Evidence** | Reef_Ideal_A15_veg with a sparse canopy, 24 h: before, DT 6 s blows up at 22 min; after, DT 6 s runs and equals DT 3 s within 0.1 % (set-up, transports) at 0.55x the cost |
| **Test** | [`tests/fixes/roms-roller-substeps/run.sh`](../../../../tests/fixes/roms-roller-substeps/run.sh), and 24 h Batch runs (below) |
| **Upstream** | not reported yet |

## In short

With `ROLLER_RENIERS`, ROMS carries the area of the surface roller of breaking
waves (`rollA`) with its own evolution equation (Reniers et al. 2004): a
source from wave breaking (`WEC_ALPHA` times the breaking dissipation), a
dissipation sink, and advection at the speed of the current plus the wave
celerity. `wec_roller.F` solves it with an explicit first-order upwind step,
`numits` sub-steps per baroclinic step. In COAWST v3.9:

```fortran
!     numits=30
      numits=1
```

The explicit upwind step is stable only while its Courant number,
(|current + wave celerity|) DT / dx, stays below 1. On a reef crest the wave
celerity is 3-6 m/s (sqrt(g h) for 1-3 m of water); with 20 m cells, DT 6 s
gives 1.1-1.6 and the roller amplifies itself from cell to cell. The
original code took 30 sub-steps; a later version takes one.

## How it was found

An idealized fringing reef (Reef_Ideal_A15, 20 m cells across the crest,
DT 6 s, Hs 1 m) blew up 22-23 min after the waves reached the reef, every
time at the surface at the inner edge of the crest next to the pass: the
vertical Courant number rose from 0.5 to 25 within four steps. The same
run with `WEC_ALPHA` 0.2 instead of 0.5 blew up at the same place one
minute later; at DT 3 s it ran a full day. A smaller roller did not help, a
smaller time step did: the signature of a Courant limit.

## The change

Before the roller loop, the routine computes the largest outflow Courant
number of the upwind scheme over the domain, using the same face speeds as
the fluxes,

    C = DT pm pn ( |u_face1| on_u + |u_face2| on_u + |v_face1| om_v + |v_face2| om_v )

with `u_face = ubar + kx/k c` (current plus the wave celerity along the wave
direction), takes its maximum over all MPI processes (`mp_reduce`, so every
process takes the same number of sub-steps and the halo exchanges inside the
loop stay matched), and sets

    numits = MAX(1, CEILING(C / 0.9))

The existing loop already divides DT by `numits` in the advection and in the
source/sink terms.

Limits: with ROMS's serial tiling (several tiles in one process, no MPI) each
tile computes its own `numits`; the result is still stable but tiles may
differ in sub-stepping. Every MPI build has one tile per process.

## Engine test results

**Cloud Batch, 24 h** (2026-11-03): Reef_Ideal_A15_veg with a density-1
canopy, waves (Hs 1 m, Tp 10 s, triads on), `ROLLER_RENIERS`, 10 + 6
processes, unsegmented:

| Run | outcome | lagoon set-up | crest transport | crest jet max | wall s per sim h |
|---|---|---|---|---|---|
| before, DT 6 s, `WEC_ALPHA` 0.5 | blew up at 21.8 min | - | - | - | - |
| before, DT 6 s, `WEC_ALPHA` 0.2 | blew up at 22.9 min | - | - | - | - |
| before, DT 3 s, `WEC_ALPHA` 0.5 (reference) | 24 h | 22.8 mm | 653 m3/s | 0.33 m/s | 110 |
| after, DT 6 s, 0.5 | 24 h | +0.1 % | +0.1 % | -3.7 % | 61 |
| after, DT 3 s, 0.5 | 24 h | 0.0 % | 0.0 % | -3.9 % | 107 |

After the patch the roller runs at DT 6 s and reproduces the DT 3 s answer;
**Local test** (tests/cases/Reef_Ideal_A15, bare reef, 40 min, DT 6 s,
`WEC_ALPHA` 0.5, 2026-11-03): PASS. Before, ROMS blows up at 21.4 min (step
214, the inner edge of the crest beside the pass); after, the run reaches
40 min; builds without the roller give identical executables before and
after.

## Who is affected

Every run with `ROLLER_RENIERS` whose roller Courant number exceeds 1:
coarse time steps, fine grids, deeper breaking zones. Such runs blew up; runs
that stayed below 1 change slightly (the sub-steps follow the time step).
