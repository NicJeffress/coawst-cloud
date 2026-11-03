# roms-quicksave-uv.patch: the quicksave file's 3-D velocity was never written

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | output only: the quicksave file's `u` and `v` now hold the 3-D velocity instead of fill values; the model and every other output are bit-identical |
| **Default** | on |
| **Files** | `ROMS/Utility/wrt_quick.F` (`wrt_quick_nf90`) |
| **Evidence** | Reef_Ideal_A15, 30 min, quicksave every 10 min: before, `u` and `v` are fill values at every point; after, they equal the history file's `u` and `v` exactly at all 4 common times; the history files bit-identical before and after |
| **Test** | [`tests/fixes/roms-quicksave-uv/run.sh`](../../../../tests/fixes/roms-quicksave-uv/run.sh), see its [README](../../../../tests/fixes/roms-quicksave-uv/README.md) |
| **Upstream** | already fixed in upstream ROMS (myroms/roms, `wrt_quick_nf90` writes both); COAWST v3.9 carries the older code. Not reported to COAWST yet |

## In short

ROMS's quicksave file (`QCKNAME`, every `NQCK` steps) is a light, frequent
output for selected fields. With `Qout(idUvel)` and `Qout(idVvel)` set to `T`
in `ocean.in`, `def_quick` defines the 3-D velocity components `u` and `v` in
the file, but in COAWST v3.9 only the Parallel-IO writer (`wrt_quick_pio`)
writes them; the standard NetCDF writer (`wrt_quick_nf90`), the one every
build without PIO uses, goes straight from the 2-D velocity to the surface
velocity. The variables are created and stay at their fill value (1e37) in
every record, without any message. The rotated components (`u_eastward`,
`v_northward`, `Qout(idu3dE/idv3dN)`), `w` and the 2-D fields are written.

Found in an engine test of `OMEGA_IMPLICIT` that read the pass jet from
minute-by-minute quicksaves: `u` and `v` were all fill values.

## The change

Two blocks in `wrt_quick_nf90`, before the surface velocity, written as the
routine writes its other 3-D fields (`nf_fwrite3d` on the u- and v-points
with the full masks), mirroring the PIO writer:

```fortran
      IF (Qout(idUvel,ng)) THEN
        scale=1.0_dp
        gtype=gfactor*u3dvar
        status=nf_fwrite3d(ng, model, QCK(ng)%ncid, idUvel,             &
     &                     QCK(ng)%Vid(idUvel),                         &
     &                     QCK(ng)%Rindex, gtype,                       &
     &                     LBi, UBi, LBj, UBj, 1, N(ng), scale,         &
# ifdef MASKING
     &                     GRID(ng) % umask_full,                       &
# endif
     &                     OCEAN(ng) % u(:,:,:,NOUT))
        ...
      END IF
```

and the same for `v` (`v3dvar`, `vmask_full`, `OCEAN(ng)%v`).

## How the test works

Reef_Ideal_A15 (coupled, periodic), built with the whole series without and
with this patch, 30 min, ROMS 1 x 2 + 2 SWAN, history and quicksave every 10
min with `Qout(idUvel)` and `Qout(idVvel)` switched on (`OCEANSED`), the
quicksave file written into `output/`:

- *bug*: before, quicksave `u` and `v` are fill values everywhere;
- *fixed*: after, they equal the history `u` and `v` at every common time;
- *unchanged*: the history files are bit-identical before and after.

## Engine test results

Run 2026-11-03 on the control VM: PASS. Before, `u` and `v` all fill values;
after, equal to the history at all 4 common times (largest difference 0 m/s);
history bit-identical.

## Who is affected

Anyone reading 3-D currents from quicksave files of a COAWST build without
PIO (the standard). Workaround before the patch: use `u_eastward` and
`v_northward` (rotated to east/north at rho points) or the history file.
