# roms-wec-stokes-fixes.patch: the u-point spectral Stokes drift loop now mirrors the v-point loop

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | yes, for runs with `SPECTRUM_STOKES` (the v3.9 default whenever SWAN is coupled and `BULK_STOKES` is not set): up to a few % of the u-point Stokes drift where the wave field changes fast between cells (3.7 % in Inlet_test), negligible where it is smooth; ROMS also runs faster |
| **Default** | on |
| **Files** | `ROMS/Nonlinear/WEC/wec_stokes.F` (`u_tail_neighbour`, `u_bin_limit`, `u_unused_sinh`) |
| **Evidence** | source check: three differences between the u and v loops stock, none patched; Inlet_test: u_stokes changes by up to 1.1 of 30 mm/s, ROMS about 20 % faster |
| **Test** | [`tests/fixes/roms-wec-stokes-fixes/run.sh`](../../../../tests/fixes/roms-wec-stokes-fixes/run.sh), see its [README](../../../../tests/fixes/roms-wec-stokes-fixes/README.md) |
| **Upstream** | not yet reported to COAWST |

## In short

ROMS computes the Stokes drift (the net drift of water particles under
waves) separately at the two kinds of velocity points of its grid, u points
and v points, in two loops that should be mirror images of each other. The
u-point loop was evidently written by copying the v-point loop, and three
v-point details survived the copy. One of them takes a wave property from the
wrong neighbouring cell; the other two only waste time. All three are fixed:
the u loop now matches the v loop exactly.

| Change | What was wrong | Effect |
|---|---|---|
| `u_tail_neighbour` | the u-point high-frequency tail averaged the wavenumber over the v-point neighbours `(i,j-1)` instead of `(i-1,j)` | u-point Stokes drift wrong where the wave field varies in y (3.7 % in Inlet_test) |
| `u_bin_limit` | the u loop added frequency bins up to kD = 200 instead of 36 | none on results (bins beyond add about e^-36); wasted time |
| `u_unused_sinh` | the u loop computed a SINH it never used | wasted time |

## Background: the Stokes drift in COAWST

In COAWST's vortex-force formulation of wave-current interaction (`WEC_VF`),
ROMS needs the Stokes drift profile `u_s(z)` at every velocity point. Two
options exist: a bulk formula from Hs, period and direction (`BULK_STOKES`),
or, since COAWST v3.8, the full calculation from SWAN's directional
spectrum (`SPECTRUM_STOKES`; COAWST commit c6c108b "add Spectrum Stokes",
February 2023; method of Liu, Kumar, Harcourt and Perrie 2021). Since v3.9
the spectral one is the default whenever SWAN is coupled.

For the spectral calculation SWAN sends ROMS, for each frequency bin, the
wavenumber (`spec_wn`) and the two components of the bin's Stokes transport
(`spec_us`, `spec_vs`), at cell centres. ROMS's velocities live on the cell
faces: u at the east-west faces (between cells `i-1` and `i`), v at the
north-south faces (between `j-1` and `j`). So every cell-centred quantity is
first averaged to the face:

```
   u point (i,j):  average of cells (i-1,j) and (i,j)
   v point (i,j):  average of cells (i,j-1) and (i,j)
```

Then, per face, level and bin, the drift is summed over the frequency bins
(`sdrx` for u, `sdry` for v), with an analytic tail added above SWAN's
highest frequency. The loop over bins stops when the bins can no longer
contribute: when `kD`, the wavenumber times the depth, exceeds `kD2deep`
(36), the bin's contribution at the bottom decays like e^-kD and is
negligible.

## u_tail_neighbour: the tail took the wavenumber from the wrong cells

In the block that adds the high-frequency tail, the u loop averaged the
wavenumber over `(i,j-1)` and `(i,j)`, the v-point neighbours, while the very
next line of the same block averages `spec_us` over `(i-1,j)` and `(i,j)`,
like every other u-point average in the routine:

```fortran
-              cff3=0.5_r8*fac3*(spec_wn(i,j-1,is)+spec_wn(i,j,is))
+              cff3=0.5_r8*fac3*(spec_wn(i-1,j,is)+spec_wn(i,j,is))
               cff2=-0.5_r8*cff3*(cff6+cff7)
               ...
               sdrx=sdrx+0.5*(spec_us(i-1,j,is)+spec_us(i,j,is))*facto2
```

So at a u point the tail used the wavenumber half a cell north-south of where
the drift is computed, instead of half a cell east-west. Where the wave field
is smooth, the two averages are nearly equal and the error is tiny; where the
wavenumber changes quickly between cells (shoaling over a reef edge, an
inlet), it is not.

## u_bin_limit and u_unused_sinh: wasted work

The u loop added bins `while (cff2 < kDmax)`, with `kDmax` = 200, while its
own comment and the v loop use `kD2deep` = 36:

```fortran
             DO WHILE ((is.lt.MSCs).and.                                  &
-     &                ((cff2.lt.kDmax).or.(k.eq.N(ng))))
+     &                ((cff2.lt.kD2deep).or.(k.eq.N(ng))))
               cff4 = 0.5_r8*cff3*(cff6-cff7)
-              cff5 = (2.0_r8*cff4*SINH(0.5_r8*cff3)**2.0_r8)
```

Bins with kD between 36 and 200 contribute about e^-36 (1e-16) of the
surface value, so this changes nothing measurable but evaluates up to five
times as many bins. And `cff5`, one more SINH per bin, level and face, was
computed and never used (upstream removed the same line from the v loop in
2024, COAWST commit 010c43b, but not from the u loop).

## How the test works

`tests/fixes/roms-wec-stokes-fixes/run.sh` ([README](../../../../tests/fixes/roms-wec-stokes-fixes/README.md)):

1. **Source check** (`check_source.py`) on the source before and after the
   patch: in the u loop no spectral average may use the `(i,j-1)` neighbour;
   in the v loop none the `(i-1,j)` neighbour; both loops must add bins while
   `cff2 < kD2deep`; the u loop must not compute `cff5`. Stock COAWST fails
   all three, the patched source passes. This is the exact test of the fix:
   the two loops are now consistent.
2. **Effect on a model run:** stock Inlet_test (which uses `SPECTRUM_STOKES`)
   before and after the patch, 2 h, compared in the Stokes drift and the
   currents, plus wall time.

## Engine test results

Run 2026-10-30. "Before" is the series up to this patch, "after" adds this
patch; stock Inlet_test, compiler flags as shipped.

**1. Source check:**

```
stock:   u-point loop: 5 spectral averages, 1 use the i,j-1 neighbour
           (cff3=0.5_r8*fac3*(spec_wn(i,j-1,is)+spec_wn(i,j,is)))
         u-point loop adds bins while cff2 < kDmax
         v-point loop adds bins while cff2 < kD2deep
         u-point loop computes cff5: yes                 -> INCONSISTENT
patched: 0 wrong neighbours, both kD2deep, no cff5       -> CONSISTENT
```

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
neighbouring cells. The v-point drift (code unchanged) changes only through
the feedback on the flow. In a smoother idealized reef case the same fix
changed u_stokes by only 1.6e-6 m/s after 1 h: how much it matters depends on
how fast the wavenumber varies in y.

**Speed.** Fewer frequency bins in the u loop and one SINH less per bin make
ROMS faster. Wall time for 2 h, each run on its own c2d-standard-4 Spot VM
(Cloud Batch): before 238 s and 240 s, after 162 s and 220 s, so about 20 %
faster on average, with a large spread between the two patched runs (machine
noise); a single pair on the control VM gave 216 s and 130 s.

**Reproducibility.** The two Batch runs of each image (c2d, AMD EPYC Milan)
were bit-identical to each other and to the control VM run (c3d, AMD EPYC
Genoa) of the same image.

## Who is affected

Every coupled run with `SPECTRUM_STOKES`, which is v3.9's default with SWAN.

## Related

`2-improvements/roms-wec-stokes-fast.patch` (later in the series) computes the
same loops with about 3x fewer SINH/COSH/EXP calls; it needs this fix first.

## References

- Liu, G., Kumar, N., Harcourt, R., Perrie, W. (2021): Bulk, spectral and deep
  water approximations for Stokes drift: implications for coupled
  ocean circulation and surface wave models. Journal of Advances in Modeling
  Earth Systems 13, doi:10.1029/2020MS002172.
