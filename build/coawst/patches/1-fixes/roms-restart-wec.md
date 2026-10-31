# roms-restart-wec.patch: exact ROMS restarts with waves, rivers and GLS turbulence

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | restarts only: a run restarted from a `PERFECT_RESTART` file now continues as the uninterrupted run (to round-off); runs without restarts are unchanged |
| **Default** | on (all changes inside `PERFECT_RESTART` with `WEC`, or in the restart file's writing) |
| **Files** | `ROMS/Utility/wrt_rst.F`, `def_rst.F`, `get_state_nlm_nf90.h`; `ROMS/Nonlinear/main3d.F`, `initial.F`, `set_massflux.F`; `ROMS/Modules/mod_ncparam.F`; `ROMS/External/varinfo.yaml` |
| **Evidence** | idealized reef with waves and a canopy, and with a river: restarted after 30 of 60 min, stock drifts away from the uninterrupted run, patched agrees to round-off (results below) |
| **Test** | [`tests/fixes/roms-restart-wec/run.sh`](../../../../tests/fixes/roms-restart-wec/run.sh), see its [README](../../../../tests/fixes/roms-restart-wec/README.md) |
| **Upstream** | not reported yet |

## In short

A long run on cheap, interruptible cloud machines (Spot VMs) must be cut into
segments, each starting from the restart files the previous one wrote. For
that to be trustworthy, a restarted run must continue exactly as if it had
never stopped. ROMS's `PERFECT_RESTART` option is meant to guarantee this,
but with COAWST's wave coupling it did not: some of the state that the first
step after a restart needs was not in the restart file, or was written with
the land mask applied where it should not have been. The restarted run then
started from a slightly different state and drifted away (2.4 cm/s within
30 min in an idealized reef case). This patch writes and reads the missing
state. Together with SWAN's own restart fix (`swan-exact-restart`), a
restarted coupled run now follows the uninterrupted one to round-off.

| Change | What was missing | Why the first step after a restart needs it |
|---|---|---|
| `wec_geopotential` | the wave-induced pressure term `zetat` | the pressure gradient uses the value from the previous step |
| `volume_fluxes` | the volume fluxes `Huon`, `Hvom` | they are computed before the coupling exchange, with the Stokes drift of the previous exchange, which the restart file no longer holds |
| `stokes_read_back` | `u_stokes`, `v_stokes` were written but never read | (completeness; they are recomputed before use) |
| `unmasked_fields` | river fluxes, GLS turbulence fields and bed properties were written with land points replaced by fill values | river face fluxes sit on land/water faces, and GLS uses values next to land |

## Background: what a perfect restart needs

A model step updates the state from time n to n+1. Most of the state is
obvious (velocities, sea level, temperature, turbulence), but every time
scheme also uses some quantities computed in an earlier step, or computed at
a different point of the cycle than where the restart file is written. A
"perfect" restart must store every such quantity exactly (in double
precision) and put it back exactly where the uninterrupted run would have it.

With waves, COAWST's step order matters. Within one baroclinic step,
`main3d.F` computes the volume fluxes (`set_massflux`, using the Stokes drift)
before the coupling exchange with SWAN; the exchange then brings new wave
fields; `wec_stokes` updates the Stokes drift; and only then is the restart
record written. In `rhs3d.F`, the pressure gradient (`prsgrd`) runs before
the wave vortex-force terms (`wec_vf`), so it uses the wave geopotential from
the previous step. Each of these lags is a quantity a restart must carry.

## wec_geopotential: the wave pressure term was zero after a restart

`zetat`, the quasi-static wave geopotential (`-g zetaw - (g qsp - bh)`), is
used by the pressure gradient one step late. It was not in the restart file,
so after a restart it was zero for one step: in the idealized reef case, the
currents were 2 cm/s off 30 min later. The patch adds `zetat` to the restart
file (new variable, `idWztt`, `varinfo.yaml`, `mod_ncparam.F`), writes it in
`wrt_rst.F` and reads it in `get_state` under `PERFECT_RESTART` and `WEC_VF`.

## volume_fluxes: the first step recomputed the fluxes with the wrong Stokes drift

The fluxes `Huon`, `Hvom` of a step are computed at its start, before the
coupling exchange, with the Stokes drift of the previous exchange. The
restart file is written after the exchange, when the Stokes drift is already
the new one. So a restarted run recomputed its first fluxes with the new
Stokes drift, not the one the uninterrupted run used. The patch writes
`Huon` and `Hvom` to the restart file (`idHUav`, `idHVav`), and the first step
after a restart uses them instead of recomputing them (`main3d.F`); a new
`exchange_massflux` (`set_massflux.F`) fills their halo and periodic columns,
and `initial.F` keeps them.

## stokes_read_back: Stokes velocities written but not read

COAWST writes `u_stokes`, `v_stokes` to the restart file but did not read
them back. They are recomputed before use, so this only makes the restored
state complete.

## unmasked_fields: river fluxes and turbulence fields lost at land points

When ROMS writes a field to a NetCDF file it normally replaces the values at
land points (where the mask is 0) with a fill value. For most fields that is
harmless. Not here:

- **River face fluxes.** A river entering as a face source (`LuvSrc`) flows
  through a cell face between a land cell and a water cell, which is a masked
  velocity point. Its volume flux in `Huon`/`Hvom` therefore sat on a masked
  point and was replaced by the fill value in the restart file: after a
  restart the river was missing from the first step's fluxes.
- **GLS turbulence fields.** The GLS closure's `Akk`, `Akp` and `Lscale` at
  land points are used in averages next to the coast.
- **Bed properties** (`bottom`), used next to land in the same way.

The patch writes these with `SetFillVal = .FALSE.`, so the values at land
points are written as they are:

```fortran
     &                   GRID(ng) % Huon,                              &
     &                   SetFillVal = .FALSE.)
...
-     &                   MIXING(ng) % Akk)
+     &                   MIXING(ng) % Akk,                           &
+     &                   SetFillVal = .FALSE.)
```

## What is unchanged

All changes are inside `PERFECT_RESTART` with `WEC` (or `WEC_VF`), or only
change what values land points get in the restart file; other builds compile
as before, and runs without a restart are unchanged. A restart file from
before the patch lacks the new variables: reading one leaves them zero (the old
behaviour), but appending to one (`LDEFOUT = F`) stops with "variable not
found".

## How the test works

`tests/fixes/roms-restart-wec/run.sh` ([README](../../../../tests/fixes/roms-restart-wec/README.md))
runs, for each of two idealized reef variants, an uninterrupted 60 min run and
the same run stopped at 30 min and restarted from its restart files (ROMS
`PERFECT_RESTART`, SWAN binary restart files), before and after the patch, and
compares the restarted run with the uninterrupted one at 60 min:

- **veg**: `tests/cases/Reef_Ideal_A15_veg` (waves, canopy, GLS);
- **river**: `tests/cases/Reef_Ideal_A15` with a river: three face sources on
  the land wall of the lagoon, 5 m3/s each, in the top layers
  (`make_river.py`).

All builds include the fixes (so SWAN's restart is exact:
`swan-exact-restart`) and the two improvements A15's SWAN setup needs.

## Engine test results

Run 2026-10-31; images built on the control VM, each variant's three runs on
one Cloud Batch c2d-standard-8 Spot VM (ROMS 1x6 + 2 SWAN; straight about
250-280 s, each part about 125-140 s). Restart at 30 min, compared at 60 min
(largest difference, restarted minus straight). PASS.

| Variant | Before the patch | After the patch |
|---|---|---|
| `veg` (waves, canopy, GLS) | currents 2.7e-5 m/s, AKv 2.3e-5, SWAN Hs 6.9e-6 m | currents **1.2e-10 m/s** (round-off), SWAN Hs **bit-identical** |
| `river` (waves, GLS, 3 face sources) | currents **2.1e-2 m/s**, AKv 4.0e-2, tke 2.7e-3, SWAN Hs 9.5e-4 m | currents 2.4e-7 m/s, SWAN Hs 2.4e-7 m |
| no-river baseline (the river image, river off) | | currents 1.8e-7 m/s, SWAN Hs 1.2e-7 m |

**With a river the restart was off by 2 cm/s** after 30 min (the river's
volume flux was missing from the first step after the restart, and the
turbulence next to the river face started from fill values). With the patch
the river run restarts as well as the same case without the river.

**A small residual remains in the base A15 case**, river or not: 1.8e-7 m/s
(no river) and 2.4e-7 m/s (river) at 60 min, against 1.2e-10 m/s for the
canopy variant. The restored state itself is exact (part2's first record, at
30 min, is bit-identical to the straight run's); the difference appears
during the next steps, on the reef crest (rows 31-44) and at the periodic seam
(i = 1), not at the river, and jumps around from record to record (3e-8 m/s at
40 min, 2e-9 at 50, 2e-7 at 60). That pattern points to something at the level
of round-off that the fast crest flow amplifies (the canopy variant's damped
crest flow keeps it at 1e-10), rather than a missing piece of state. Not
traced further; it is five orders of magnitude below the 2 cm/s the patch
removes. The test therefore checks the river variant against this no-river
baseline (no more than 3 times it), and the canopy variant against round-off
(below 1e-8 m/s).

Earlier results with the same changes (2026-10-24, control VM, canopy
variant, 6 ROMS + 2 SWAN), adding the pieces one at a time:

| Pieces | max current difference at 60 min | SWAN |
|---|---|---|
| COAWST as shipped (text SWAN restart) | 2.4e-2 m/s | Hs 1.3e-3 m off, no plants at the restart |
| SWAN binary restart only (`swan-exact-restart`) | 5e-4 m/s | Hs 2e-5 m |
| + `wec_geopotential` | 4e-5 m/s | Hs 2e-5 m |
| + `volume_fluxes`, SWAN's post-exchange state | 1e-7 m/s | Hs 2e-7 m |
| + halo exchange of the fluxes (final) | 2e-10 m/s (round-off) | bit-identical |

And on 2026-10-29, tracing rivers on the coast of an interior land peninsula
in the stratified A15 variant: 1.6e-3 m/s and 0.03 in salinity off 10 min after
the restart before the masked-point changes, 3.7e-9 m/s (round-off) after all
three of them (fluxes, GLS fields, bed properties).

## Who is affected

Any run with waves (`WEC`) restarted from a `PERFECT_RESTART` file: segmented
runs on interruptible machines, runs continued after a crash or a time limit.
Rivers as face sources and GLS turbulence add to it.
