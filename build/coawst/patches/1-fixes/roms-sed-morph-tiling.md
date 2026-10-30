# roms-sed-morph-tiling.patch: sediment morphology results depended on the MPI tiling

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | yes, for runs with `SED_MORPH` on more than one ROMS tile; one-tile runs are bit-identical to stock |
| **Default** | on (all lines inside `SEDIMENT` + `SED_MORPH`, `DISTRIBUTE`, or `SED_WENO` code) |
| **Files** | `ROMS/Nonlinear/step2d_LF_AM3.h`, `ROMS/Nonlinear/Sediment/sed_bed.F`, `ROMS/Nonlinear/Sediment/sed_bedload_vandera.F` |
| **Evidence** | Inlet_test: ROMS on 1x1 and 1x2 tiles differ by 12 mm in bathymetry after 12 h stock; bit-identical with the patch (results below) |
| **Test** | [`tests/fixes/roms-sed-morph-tiling/run.sh`](../../../../tests/fixes/roms-sed-morph-tiling/run.sh) |
| **Upstream** | not yet reported to COAWST |

## Summary

ROMS splits the grid into tiles (`NtileI` x `NtileJ`), one per MPI process.
A correct parallel model gives the same answer for any tiling, to the last
bit, because every tile copies the values it needs from its neighbours into a
border of "ghost" (halo) points before using them. With sediment morphology
(`SED_MORPH`: the bed level, and so the water depth `h`, changes as sand
moves), three places in COAWST v3.9 either did not refresh the halo after
changing a field, or read halo values that were never computed. The result:
the answer depended on how many processes ROMS ran on. In COAWST's own
Inlet_test, 1x1 and 1x2 tiles differed by 12 mm in bathymetry and 0.17 mm in
sea level after 12 h.

Why it matters: results that change with the number of processes cannot be
reproduced on a different machine or layout, and the differences grow with
time in morphology runs. The size of the error at each tile edge is not
bounded by anything physical; it depends on how fast the bed changes there.

## The three bugs

### 1. `h` not refreshed in the halo during the barotropic steps (`step2d_LF_AM3.h`)

With `SED_MORPH`, ROMS adds the bed change to `h` at every barotropic (fast)
time step, but only on the tile's own points (`Istr:Iend`, `Jstr:Jend`). The
halo copies of `h` were refreshed only by `set_depth`, after all the fast
steps of a baroclinic step. In between, fluxes across a tile edge used the
neighbour's old depth.

Fix: exchange `h` together with `zeta`, in the exchange that already follows
the update of the free surface. For one process (no MPI) the periodic
exchange `exchange_r2d_tile` gets the same addition.

```fortran
#ifdef DISTRIBUTE
# if defined SEDIMENT && defined SED_MORPH
      CALL mp_exchange2d (ng, tile, iNLM, 2,                            &
     &                    LBi, UBi, LBj, UBj,                           &
     &                    NghostPoints,                                 &
     &                    EWperiodic(ng), NSperiodic(ng),               &
     &                    zeta(:,:,knew), h)
# else
      CALL mp_exchange2d (ng, tile, iNLM, 1, ... zeta(:,:,knew))
# endif
#endif
```

### 2. `bed_thick` halo never refreshed under MPI (`Sediment/sed_bed.F`)

`sed_bed` recomputes `bed_thick(:,:,nnew)` and `bed_thick(:,:,3)` on the tile
only; the code exchanged them for periodic boundaries but had no MPI
exchange. With MPDATA tracer advection (Inlet_test's sand uses it),
`step3d_t.F` reads both in the halo (`IstrUm2:Iendp2i`). Fix: an
`mp_exchange2d` of both fields after they are computed.

### 3. The WENO bedload stencil read values that were never computed (`Sediment/sed_bedload_vandera.F`)

`sed_bedload_vandera.F` hard-codes `#define SED_WENO`. The bedload flux at a
tile's last face (`Iend+1`, `Jend+1`) uses the cell fluxes `FX_r`, `FE_r` up
to `Iend+3`, `Jend+3`, but the loops computed them only up to
`Iendp2i`/`Jendp2i` (two points out). The stencil then read whatever was in
memory there. It matters only where the upwind side is the far side, so in
Inlet_test it first changed results after 3.4 h (step 204, rows 35/36), when
sand at the tile edge started moving south. Fix: compute both loops up to
`Iendp3`/`Jendp3` (three points out inside the domain, clipped to the
boundary row at a domain edge).

## How the bugs were found

Inlet_test with 1 SWAN process and ROMS history at every step: find the
first step and place where 1x1 and 1x2 differ; rebuild with options switched
off (`SED_MORPH` off removed every difference; bedload off, or
`-ffp-contract=off`, did not); then print every input of the bedload face flux
at the two cells that first differed. The inputs matched; the face flux did
not, which led to the stencil reach.

## Results

Original investigation (2026-10-20, Inlet_test 12 h, control VM): with the
patch, 1x1 and 1x2 bit-identical over the full 12 h; 1 ROMS + 1 SWAN against
1x2 ROMS + 6 SWAN identical in every ROMS output; one-tile results
bit-identical to the unpatched build; no measurable cost (172 s patched,
174 s unpatched for 12 h on 1x2 ROMS + 6 SWAN).

Engine test (`tests/fixes/roms-sed-morph-tiling/run.sh`, stock COAWST
26e6fb7 with and without this patch, nothing else changed): see
[Engine test results](#engine-test-results).

## Engine test results

Run 2026-10-30 on the control VM (4 vCPUs): stock Inlet_test (COAWST 26e6fb7,
compiler flags as shipped, `-O3 -ffast-math`), 6 simulated hours, 1 SWAN
process, ROMS on 1x1 and 1x2 tiles; "before" is stock COAWST (this is the
first patch of the series), "after" adds this patch. Hourly history
compared; Inlet_test's 1x2 split puts the tile edge between rows 35 and 36.

**Before the patch: the two tilings differ**, growing with time, at the tile
edge (largest differences at rows 33-37):

| Variable | max \|1x1 - 1x2\| at 6 h | largest value |
|---|---|---|
| bathymetry `bath` | 6.5 mm | 15.5 m |
| bed thickness | 6.6 mm | 10.1 m |
| sea level `zeta` | 0.20 mm | 0.43 m |
| depth-mean current `vbar` | 1.5 mm/s | 1.9 m/s |
| current `v` | 1.6 mm/s | 2.0 m/s |

Bathymetry difference by hour: 0, 0.27, 2.3, 4.4, 6.1, 5.5, 6.5 mm (0-6 h).

**After the patch: 1x1 and 1x2 bit-identical** in `bath`, `zeta`, `ubar`,
`vbar`, `u`, `v`, `bed_thickness`, every record. **One tile, before vs after:
bit-identical** (the patch changes nothing when ROMS runs on one tile).
Wall time 6 h: 1x1 577 s (stock) and 620 s (patched), 1x2 682 s and 485 s,
on a shared VM where other jobs ran at times; no cost of the patch is
visible in the original, cleaner measurement either (172 s vs 174 s).

## Limits: what is still tiling-dependent or not covered

- **Splits in i (2x1, 2x2) still differ at rounding level.** A
  one-rounding-unit difference in `u_wec_stress` at the tile edge (i = 38)
  appears from step 13, with or without fused multiply-add. After 12 h,
  bathymetry differs by 1e-6 m and sea level by 1.5e-8 m (stock: 12 mm and
  0.17 mm). It first shows in the wave-current terms
  (`ROMS/Nonlinear/WEC/wec_vf.F`); not traced further. Splits in j only (1xN)
  are bit-identical.
- **The same omissions in other bed models are not patched** (not used by
  Inlet_test): `sed_bed2.F` and `sed_bed_cohesive.F` (`NONCOHESIVE_BED2`,
  `COHESIVE_BED`, `MIXED_BED`) also never exchange `bed_thick(:,:,nnew)` under
  MPI and never set `bed_thick(:,:,3)`, which `step3d_t.F` uses with MPDATA.
- **Ghost points.** The WENO stencil reads 3 halo points (`Jstrm3`), but ROMS
  uses 3 ghost points only with MPDATA tracer advection or `UV_VIS4`
  (`Utility/inp_par.F`). A case with Van der A bedload and neither of those
  reads outside the halo.
- **Suspected from reading the code, not seen in Inlet_test:** at the northern
  and eastern domain edges the WENO stencil still reads `FE_r`/`FX_r` at
  `Mm+2`, `Mm+3` (`Lm+2`, `Lm+3`), which are never computed. This matters only
  when bedload in the last rows or columns moves away from the boundary.

A case that uses these code paths should be tested the same way (two
tilings, compare) and patched the same way.
