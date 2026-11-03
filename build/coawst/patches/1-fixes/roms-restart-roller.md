# roms-restart-roller.patch: the Reniers roller was lost at a restart

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | restarts with `ROLLER_RENIERS` only: a restarted run now keeps its roller and continues as the uninterrupted run. Runs without restarts, and builds without `ROLLER_RENIERS`, are unchanged |
| **Default** | on (all changes inside `WEC_ROLLER` and `ROLLER_RENIERS`) |
| **Files** | `ROMS/Nonlinear/WEC/wec_roller.F`, `ROMS/Utility/def_rst.F`, `wrt_rst.F`, `get_state.F`, `get_state_nlm_nf90.h` |
| **Evidence** | idealized reef with waves and the roller, restarted halfway: 30 min after the restart, before 6.4e-4 m/s off, after 5.8e-11 m/s (round-off); without the roller, bit-identical output |
| **Test** | [`tests/fixes/roms-restart-roller/run.sh`](../../../../tests/fixes/roms-restart-roller/run.sh), see its [README](../../../../tests/fixes/roms-restart-roller/README.md) |
| **Upstream** | not reported yet |

## In short

With `ROLLER_RENIERS`, ROMS carries the area of the surface roller of breaking
waves, `rollA`, from step to step with its own evolution equation (Reniers
et al. 2004; see `roms-roller-substeps`). It is model state, like the
velocities: each step starts from the previous step's roller. COAWST did not
write it to the restart file, so a restarted run started with no roller at
all (`rollA` = 0 everywhere). The roller then grew back from the breaking
source over the next minutes, and in that time the wave forcing on the reef
flat was missing its roller part: the restarted run drifted away from the
uninterrupted one.

The patch writes `rollA` and the roller's dissipation `Dissip_roller` to the
restart file, reads both back under `PERFECT_RESTART`, and skips the roller
update in the first step after such a restart, because the stored values
already include it (below).

The other roller options (`ROLLER_SVENDSEN`, `ROLLER_MONO`) compute the roller
from the current wave field at every step and need no restart state.

## Why storing rollA alone is not enough

In `main3d`, a step runs the wave routines (`wec_roller`, then `wec_stokes`)
right after the coupling exchange, and only then `output`, which writes the
history and restart records, and then `rhs3d` and the time stepping. So the
restart record of step n is written inside step n + 1, after `wec_roller` has
already moved the roller to its step n + 1 value. A restarted run that reads
that `rollA` and runs `wec_roller` again in its first step advances the roller
twice. A first version of this patch did exactly that: restored `rollA`, and
the restarted run was 1.3e-3 m/s off, twice as far as with no roller in the
restart at all (6.4e-4 m/s).

So the first step after a perfect restart must use the stored roller as it
is. `Dissip_roller`, the roller's dissipation, is computed inside the same
roller loop and used later in the step (`wec_vf` in `rhs3d`, `wec_wave_mix`),
so it is stored too. In `wec_roller.F`, after the sub-step count is set
(`roms-roller-substeps`):

```fortran
#  ifdef PERFECT_RESTART
!
!  roms-restart-roller: the restart record is written after this routine
!  has updated the roller in that step (output follows it in main3d), so
!  rollA and Dissip_roller read from a perfect restart file are already
!  the values of the first step. Take no roller step then; the exchanges
!  below still fill the ghost points.
!
      IF (PerfectRST(ng).and.(iic(ng).eq.ntstart(ng))) numits=0
#  endif
```

## The change

COAWST already has variables for both fields: `idWrol` ("wave roller action
density" in `varinfo.yaml`) and `idWdis` (the roller dissipation), both
`r2dvar`. The patch uses them for the restart file:

- `def_rst.F`: defines both (2-D, record dimension last, `sr2dgrd`);
- `wrt_rst.F`: writes `FORCES(ng)%rollA` and `FORCES(ng)%Dissip_roller` with
  `nf_fwrite2d`;
- `get_state_nlm_nf90.h`: reads them with `nf_fread2d` under
  `PERFECT_RESTART` (`IF (Perfect2D)`); a restart file without them leaves
  them zero, the old behaviour;
- `wrt_rst.F` and `get_state.F`: `USE mod_forces` under the same `#if` (both
  use it already only with `ICE_MODEL` or the adjoint options, so a roller
  build otherwise fails to compile);
- `wec_roller.F`: no roller step in the first step after a perfect restart
  (above).

## How it was found

A 24 h density-1-canopy A15 run with the roller (`WEC_ALPHA` 0.5, DT 6 s,
after `roms-roller-substeps`) was run straight and in 4 h segments on Cloud
Batch (restart files from `PERFECT_RESTART`, SWAN binary restarts). At hour 8,
four hours after the restart, the segmented run was 1.4e-4 m/s off the
straight one. The same pair without the roller was 3.7e-7 m/s off: the roller
made the restart 400 times worse. `rollA` was not in the restart file.

## Test results

`tests/fixes/roms-restart-roller/run.sh`, tests/cases/Reef_Ideal_A15 with
`+ROLLER_RENIERS` and `WEC_ALPHA` 0.5, ROMS 1 x 2 + 2 SWAN, DT 6 s: 60 min
straight against 30 + 30 min restarted, compared at 60 min (2026-11-03):

| | currents | ubar, vbar | zeta | AKv | SWAN Hs |
|---|---|---|---|---|---|
| before | 6.4e-4 m/s | 2.5e-4, 3.5e-4 m/s | 1.4e-5 m | 1.1e-3 m²/s | 1.2e-4 m |
| first version (`rollA` only) | 1.3e-3 m/s | 5.0e-4, 7.0e-4 m/s | 2.8e-5 m | 3.0e-3 m²/s | 2.3e-4 m |
| after | **5.8e-11 m/s** | **0, 0** | **0** | 9.3e-10 m²/s | **0** |

The remaining 5.8e-11 m/s is round-off, the level of the other A15 restart
tests (`roms-restart-wec`). Builds without the roller (10 min runs, history
every 2 min): the history files before and after the patch are bit-identical.

## Who is affected

Any run with `ROLLER_RENIERS` restarted from a `PERFECT_RESTART` file:
segmented runs on interruptible machines, runs continued after a crash or a
time limit.
