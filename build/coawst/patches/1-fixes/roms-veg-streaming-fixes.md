# roms-veg-streaming-fixes.patch: the wave streaming force inside a canopy

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | only with `VEG_STREAMING` (the canopy streaming force) and, through it, `BOTTOM_STREAMING`; builds without `VEG_STREAMING` are unchanged (bottom-streaming diagnostics aside, below) |
| **Default** | on (the code changes are inside `VEG_STREAMING` and `BOTTOM_STREAMING`) |
| **Files** | `ROMS/Nonlinear/Vegetation/vegetation_stream.F`, `ROMS/Nonlinear/WEC/wec_streaming.F`, `Master/mct_roms_swan.h` |
| **Evidence** | idealized reef with a canopy, waves and both options: the depth-integrated streaming force against the wave momentum lost to bottom friction and the plants, (Dissip_fric + Dissip_veg) k/sigma: before, 0.29 of it (rms misfit 0.71); after, 1.000 (misfit 3.5e-4); without the options, bit-identical output |
| **Test** | [`tests/fixes/roms-veg-streaming-fixes/run.sh`](../../../../tests/fixes/roms-veg-streaming-fixes/run.sh), see its [README](../../../../tests/fixes/roms-veg-streaming-fixes/README.md) |
| **Upstream** | not reported yet |

## In short

With `WEC_VF`, ROMS gives the mean flow the momentum the waves lose through
explicit forces, one per way of losing it: breaking (always on), bottom
friction (`BOTTOM_STREAMING`, a force in the wave boundary layer) and plants
(`VEG_STREAMING`, a force inside the canopy, Luhar et al. 2010). Each should
integrate over depth to the dissipation times k/sigma, the momentum the waves
carry per unit energy. In COAWST v3.9 the canopy part was wrong in four ways,
so the canopy force was a fraction of what it should be and the bottom force
was lost whenever it was on.

## What was wrong

1. **The canopy force replaced the bottom force.** `wec_streaming.F` builds
   the bottom-streaming force layer by layer and then, with `VEG_STREAMING`,
   overwrote it with the canopy force (`BWDXL(i,j)=BWDXL_veg(i,j,k)`), so with
   both options the bottom streaming was gone.
2. **The canopy force was not normalized.** `vegetation_stream.F` set the
   force in every layer to Dissip_veg k/sigma times the layer's canopy
   fraction, so its depth integral was Dissip_veg k/sigma times the canopy
   height in metres (0.4 for 0.4 m plants), not Dissip_veg k/sigma.
3. **It used the previous step's canopy fraction.** The fraction `Lveg` is
   set by `vegetation_drag`, which runs after `wec_streaming` in `rhs3d`; so
   the force used the previous step's value, and zero after a restart
   (`Lveg` is not in the restart file).
4. **No ghost points.** The force was computed on interior points only and
   the imported `Dissip_veg` was never exchanged between tiles, while
   `wec_streaming.F` averages the force to u- and v-points with the
   neighbouring point; at every tile edge and at a periodic seam the face
   force was averaged with a point that was never set.

Also: the bottom-streaming 2-D term `rubst2d` carried an extra layer
thickness (`cff*cff1`, cff already being the thickness-weighted force), so
its units were m⁵/s² instead of m⁴/s². In LF-AM3 it cancels (it enters the
2-D right-hand side and the 3-D forcing correction alike), but the 2-D
bottom-streaming diagnostic was wrong; the AB3-AM4 kernel does not use it.
And with `SWAN_IUNIFORM` the coupler wrote `FORCES(ng)%Dissip_veg`, an array
that does not exist (a compile error in an unused combination).

## The change

- `vegetation_stream.F`: computes the force on the tile and its ghost
  points, with the canopy share of each layer from the plant height and the
  layer depths of the current step: weight w_k = sum over plant types of
  Cd D n x (fraction of layer k inside the canopy) x Hz_k, force in layer k =
  Dissip_veg k cos(theta)/sigma x w_k / (Hz_k sum w). It integrates to
  Dissip_veg k/sigma and puts it where the frontal area is. The rigid plant
  height is used (`VEG_FLEX` bending is not applied).
- `wec_streaming.F`: the canopy force is added to the bottom force;
  `rubst2d`, `rvbst2d` without the extra thickness.
- `mct_roms_swan.h`: `VEG(ng)%Dissip_veg` is exchanged across tiles after the
  import (with the other wave fields); the `SWAN_IUNIFORM` lines name it.

`VEG_STREAMING` acts only together with `BOTTOM_STREAMING`, as in COAWST: the
streaming routine is compiled with `BOTTOM_STREAMING` or `SURFACE_STREAMING`
and the canopy force is applied inside the bottom-streaming block.

## Test results

`tests/fixes/roms-veg-streaming-fixes/run.sh` (2026-11-03): Reef_Ideal_A15_veg
(constant canopy, waves ramping to Hs 1 m), `+BOTTOM_STREAMING +VEG_STREAMING`,
the momentum diagnostics of step 111 against the history of step 110 (largest
Dissip_fric 1.7 W/m², Dissip_veg 4.6 W/m² at that time):

| | force / (Dissip_fric + Dissip_veg) k cos/sigma (least squares) | rms misfit |
|---|---|---|
| before | 0.293 | 0.71 |
| after | **1.000** | **3.5e-4** |

The remaining misfit is the float32 history used to rebuild the expected
value. Runs without the options: bit-identical history before and after.

**Stability.** Later in the same run (20 min, the waves near full height) the
test case blows up with the fixed force: a two-step oscillation in the bottom
layer of the crest row, then NaN at step 211. The bottom-streaming force lands
almost entirely in the bottom cell (its decay scale is the wave boundary layer,
a few centimetres, against 5 cm layers on a 0.5 m crest), and this test case
takes the bottom stress and the canopy drag explicitly. Before the fix the
force was too small to show this. The A15 cases of the options campaign take
both implicitly (`BSTRESS_IMPLICIT`, `VEG_DRAG_IMPLICIT`); their 24 h runs with
the options are in the idealized-reef notebook (2026-11-03, wave streaming).

## Who is affected

Runs with `VEG_STREAMING` (all of them: the force was a fraction of the
intended one, and the bottom streaming was lost); runs with `BOTTOM_STREAMING`
alone only in the 2-D diagnostic.
