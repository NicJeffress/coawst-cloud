# roms-wec-stokes-fixes.patch: the u-point spectral Stokes drift loop now mirrors the v-point loop

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | yes, for runs with `SPECTRUM_STOKES` (the v3.9 default whenever SWAN is coupled and `BULK_STOKES` is not set): up to a few % of the u-point Stokes drift where the wave field changes fast (3.7 % in Inlet_test), negligible where it is smooth; also faster |
| **Default** | on |
| **Files** | `ROMS/Nonlinear/WEC/wec_stokes.F` |
| **Evidence** | source check: three differences between the u and v loops stock, none patched; Inlet_test: u_stokes changes by up to 1.1 of 30 mm/s, ROMS about 20 % faster |
| **Test** | [`tests/fixes/roms-wec-stokes-fixes/run.sh`](../../../../tests/fixes/roms-wec-stokes-fixes/run.sh) |
| **Upstream** | not yet reported to COAWST |

## Summary

With waves, ROMS adds the Stokes drift (the net drift of water particles under
waves) to the currents. COAWST v3.8 added a version computed from SWAN's full
wave spectrum (`SPECTRUM_STOKES`, COAWST commit c6c108b "add Spectrum Stokes",
February 2023; method of Liu, Kumar, Harcourt and Perrie 2021, JAMES,
doi:10.1029/2020MS002172). Since v3.9 it is the default with SWAN.

`wec_stokes.F` computes the drift at u points (east-west faces of a cell) and
at v points (north-south faces) in two loops that should be mirror images of
each other: a u point averages a cell-centred field over its west and east
cells, `(i-1,j)` and `(i,j)`; a v point over its south and north cells,
`(i,j-1)` and `(i,j)`. The u loop was evidently written by copying the v loop,
and three things were not converted. All three are internal inconsistencies of
the code, present since c6c108b.

## The three fixes

1. **Wrong neighbour in the u-point high-frequency tail.** Above the
   highest SWAN frequency the drift is extended with an analytic tail that
   needs the wavenumber at the face. In the u loop it was averaged over
   `(i,j-1)`, the v-point neighbours, while the next line of the same block
   averages `spec_us` over `(i-1,j)` and every other u-point average uses
   `(i-1,j)`:

   ```fortran
   -              cff3=0.5_r8*fac3*(spec_wn(i,j-1,is)+spec_wn(i,j,is))
   +              cff3=0.5_r8*fac3*(spec_wn(i-1,j,is)+spec_wn(i,j,is))
   ```

   The effect is small where the wavenumber changes little between
   neighbouring cells, and largest where it changes fast (shoaling, reef
   edges). In an idealized reef case it changed u_stokes by up to
   1.6e-6 m/s after 1 h (largest drift 0.06 m/s).

2. **Frequency-bin limit.** The u loop added frequency bins while
   `cff2 < kDmax` (200); its own comment, and the v loop, use `kD2deep` (36).
   Bins beyond kD = 36 contribute about e^-36 of the surface value, so this
   only cost time.

3. **An unused `cff5`** (one more SINH per bin and level) in the u loop.
   Upstream removed the same line from the v loop in 2024 (COAWST commit
   010c43b) but not from the u loop.

## Test

`tests/fixes/roms-wec-stokes-fixes/run.sh SOURCE OUTDIR`:

1. **Source check** (`check_source.py`, on the series before and after the
   patch): in the u loop, no spectral average may use the `(i,j-1)` neighbour;
   in the v loop, none the `(i-1,j)` neighbour; both loops must add bins while
   `cff2 < kD2deep`; the u loop must not compute `cff5`. Stock COAWST fails all
   three, the patched source passes. Tested on the unpatched and patched
   `wec_stokes.F` of COAWST 26e6fb7:

   ```
   stock:   u-point loop: 5 spectral averages, 1 use the i,j-1 neighbour
            u-point loop adds bins while cff2 < kDmax
            v-point loop adds bins while cff2 < kD2deep
            u-point loop computes cff5: yes            -> INCONSISTENT
   patched: 0 wrong neighbours, both kD2deep, no cff5  -> CONSISTENT
   ```

2. **Effect on a model run:** stock Inlet_test (which uses `SPECTRUM_STOKES`)
   before and after the patch, compared in the Stokes drift and currents.

## Engine test results

Run 2026-10-30. "Before" is the series up to this patch
(`roms-sed-morph-tiling`), "after" adds this patch; stock Inlet_test, compiler
flags as shipped.

**1. Source check:** stock `INCONSISTENT` (as listed above), patched
`CONSISTENT`.

**2. Effect on Inlet_test** (2 simulated hours, ROMS 1x2 + 1 SWAN; history
every hour), before vs after:

| Variable | max \|before - after\| at 2 h | largest value |
|---|---|---|
| `u_stokes` (3-D) | 1.1 mm/s | 30 mm/s |
| `ubar_stokes` | 0.10 mm/s | 6.3 mm/s |
| `v_stokes` | 9e-7 m/s | 0.15 m/s |
| `ubar`, `vbar` | 0.04, 0.02 mm/s | 1.7 m/s |
| sea level | 4.6e-6 m | 0.91 m |
| bathymetry (`SED_MORPH`) | 0.07 mm | 15.5 m |

`u_stokes` differences by record (0, 1, 2 h): 2.5e-12, 1.2e-4, 1.1e-3 m/s.
The u-point drift changes by up to 3.7 % of its largest value, at the inlet
mouth (i = 43, j = 36), where the wave field changes fastest between
neighbouring cells; the v-point drift (code unchanged) changes only through
the feedback on the flow. In a smoother idealized reef case the same fix
changed u_stokes by only 1.6e-6 m/s after 1 h: how much it matters depends on
how fast the wavenumber varies in y.

**Speed.** Fewer frequency bins in the u loop (36 instead of up to 200) and
one SINH less per bin make ROMS faster. Wall time for 2 h, each run on its own
c2d-standard-4 Spot VM (Cloud Batch, 2026-10-30): before 238 s and 240 s,
after 162 s and 220 s, so about 20 % faster on average, with a large spread
between the two patched runs (machine noise); a single pair on the control VM
gave 216 s and 130 s.

**Reproducibility.** The two Batch runs of each image (c2d, AMD EPYC Milan)
were bit-identical to each other and to the control VM run (c3d, AMD EPYC
Genoa) of the same image.

## Related

`2-improvements/roms-wec-stokes-fast.patch` (later in the series) computes the
same loops with about 3x fewer SINH/COSH/EXP calls; it needs this fix first.
