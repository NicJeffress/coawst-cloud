# roms-wec-stokes-fast.patch: the spectral Stokes drift with 3x fewer SINH/COSH/EXP calls

| | |
|---|---|
| **Type** | improvement (speed) |
| **Changes results?** | rounding level only (the same formula, evaluated in a different order) |
| **Default** | on; active in every build with `SPECTRUM_STOKES`, which COAWST v3.9 defines whenever SWAN or WW3 is coupled and `BULK_STOKES` is not set |
| **Files** | `ROMS/Nonlinear/WEC/wec_stokes.F` |
| **Evidence** | idealized reef, 1 h: ROMS's wave-effects kernel 372 -> 254 CPU-s (-32 %); every field within 2e-7 of its size (last-bit differences in single-precision output) |
| **Test** | [`tests/improvements/roms-wec-stokes-fast/run.sh`](../../../../tests/improvements/roms-wec-stokes-fast/run.sh), see its [README](../../../../tests/improvements/roms-wec-stokes-fast/README.md) |
| **Upstream** | not reported yet |

## In short

When ROMS is coupled to SWAN, COAWST v3.9 computes the Stokes drift (the net
forward drift of water particles under waves) from SWAN's wave spectrum,
frequency by frequency (`SPECTRUM_STOKES`). For every velocity point, every
vertical layer and every frequency bin it evaluates a depth-averaging factor
with two hyperbolic functions (`SINH`, `COSH`), or two exponentials in deep
water. Those calls made the Stokes drift one of the most expensive parts of
ROMS in a coupled run: about a quarter of ROMS's CPU time in the idealized
reef case.

The factor can be rewritten exactly so that each value depends on one layer
interface (a W level) only, and each interface is shared by the two layers
next to it. The patch computes each interface value once and reuses it, and
computes the k-independent `SINH(kD)**2` once per frequency bin instead of
once per layer. The physics and the formula are unchanged; only the order of
floating-point operations differs, so results differ in the last bits.

| Change | Before | After |
|---|---|---|
| layer factor `sinh(a)cosh(b)` | `SINH` and `COSH` per layer and bin (deep water: 2 `EXP`) | written as a difference of one function at the layer's two W levels; each W level's value computed once and reused by the layer above |
| `SINH(kD)**2` | per layer and bin | once per bin |

## Background: the spectral Stokes drift in COAWST

For a wave spectrum, the Stokes drift at depth is a sum over frequency bins
of `u_s(f) * cosh(2k(z + h)) / sinh^2(kD)` (k the wavenumber, D the depth).
ROMS needs it averaged over each model layer, from the W level below to the
W level above. COAWST does that analytically: with `cff3 = 2 k D` and the
layer's bottom and top in nondimensional form (`cff7`, `cff6`, between -1 at
the bed and 0 at the surface), the layer average is

```
sinh(cff4) * cosh(cff3 - cff2) / (2 cff4 sinh^2(cff3/2))
```

where `cff2` and `cff4` are the layer's centre and half-thickness in the same
units. In deep water (`kD > 18`) it uses the exponential limit. The code came
in COAWST commit c6c108b ("add Spectrum Stokes", v3.8; method of Liu, Kumar,
Harcourt and Perrie 2021, JAMES, doi:10.1029/2020MS002172). The two loops
(u points and v points) were made consistent with each other by the fix
`roms-wec-stokes-fixes`, earlier in the series.

## The change

With the identity `sinh(X) cosh(Y) = (sinh(X + Y) + sinh(X - Y)) / 2`, the
numerator is

```
sinh(cff4) cosh(cff3 - cff2) = (F(cff6) - F(cff7)) / 2,   F(c) = sinh(cff3 (c + 1))
```

a function of one W level. The layer's upper W level is the lower one of the
layer above, so each value is computed once per W level and bin instead of
twice per layer. In deep water, `EXP(-cff2 + cff4) = EXP(cff3 cff6)` and
`EXP(-cff2 - cff4) = EXP(cff3 cff7)`, the same structure. The code keeps the
per-bin values of the lower (`Flo`) and upper (`Fhi`) W level and of
`SINH(kD)**2` (`den`):

```fortran
-                facto2=SINH(cff4)*COSH(cff3-cff2)/                      &
-     &                    (2.0_r8*cff4*SINH(0.5_r8*cff3)**2.0_r8+eps)
+!  sinh(cff4)*cosh(cff3-cff2) = 0.5*(F(cff6)-F(cff7)) with
+!  F(c) = SINH(cff3*(c+1)): one SINH per W level and bin.
+                IF (is.gt.nlo) Flo(is)=SINH(cff3*(cff7+1.0_r8))
+                Fhi(is)=SINH(cff3*(cff6+1.0_r8))
+                IF (is.gt.nden) THEN
+                  den(is)=SINH(0.5_r8*cff3)**2.0_r8
+                  nden=is
+                END IF
+                facto2=0.5_r8*(Fhi(is)-Flo(is))/                        &
+     &                 (2.0_r8*cff4*den(is)+eps)
               ELSE
 ...
-                facto2=0.5_r8*(EXP(-cff2+cff4)-EXP(-cff2-cff4))/        &
-     &                 (cff4+eps)
+!  EXP(-cff2+cff4) = EXP(cff3*cff6), EXP(-cff2-cff4) = EXP(cff3*cff7)
+                IF (is.gt.nlo) Flo(is)=EXP(cff3*cff7)
+                Fhi(is)=EXP(cff3*cff6)
+                facto2=0.5_r8*(Fhi(is)-Flo(is))/(cff4+eps)
```

and after each layer:

```fortran
+!  The upper W level becomes the lower one of the next layer.
+            Flo(1:is-1)=Fhi(1:is-1)
+            nlo=is-1
```

`nlo` counts the bins whose lower value is already known (the loop over bins
stops at a different bin in each layer, once the contribution is negligible),
`nden` those whose `SINH(kD)**2` is known. The same change is made in the
u-point and the v-point loops. The arrays are double precision, as the
original expressions. Where the original subtracted two nearly equal numbers
in a different order, the last bits of the result change; that is the only
difference.

## How the test works

`tests/improvements/roms-wec-stokes-fast/run.sh`
([README](../../../../tests/improvements/roms-wec-stokes-fast/README.md))
builds the idealized reef (`tests/cases/Reef_Ideal_A15`, waves from SWAN,
spectral Stokes drift) before and after the patch, both with `PROFILE` so
ROMS reports the CPU time of each part, runs both for 1 h, and compares the
last history record (Stokes drift and its depth average, currents, sea
level, eddy viscosity, turbulent kinetic energy) and the CPU time of ROMS's
"Waves Effect on Currents kernel", which contains the Stokes drift.

## Engine test results

Run 2026-10-31 on Cloud Batch, c2d-standard-8 Spot VMs (ROMS 1x6 + 2 SWAN,
1 h). PASS.

| Field (after 1 h) | largest difference | largest value | relative |
|---|---|---|---|
| `u_stokes`, `v_stokes` | 7e-9, 2.2e-8 m/s | 0.06, 0.13 m/s | 1.2e-7, 1.7e-7 |
| `u`, `v` | 3.8e-8, 1.5e-7 m/s | 0.55, 1.16 m/s | 7e-8, 1.3e-7 |
| `zeta` | 7e-9 m | 0.09 m | 8e-8 |
| `AKv`, `tke` | 1.5e-8, 3.7e-9 | | 5e-8, 1.5e-7 |

The history is written in single precision, whose last bit is about 1e-7 of
the value: the differences are flips of that last bit.

| ROMS CPU time (summed over 6 processes) | before | after |
|---|---|---|
| Waves Effect on Currents kernel | 372 s | 254 s (-32 %) |
| ROMS total (profiled) | 1374 s | 1550 s |
| wall time of the run | 238 s | 267 s |

**The wall time did not improve here**, because in this layout ROMS was not
the slow side: with 2 SWAN processes against 6 ROMS processes, ROMS spends
most of each coupling interval waiting for SWAN. That waiting is in ROMS's
profile as "Unused 04" (617 s before, 871 s after: the CPU time saved went
into waiting), which also makes ROMS's total larger. The two runs were on
different VMs, which differ by about 10 % in speed (the 2-D kernel, untouched
by the patch, took 246 s and 278 s). The saving turns into wall time when the
split gives SWAN enough processes that ROMS is the slower side; with the
patch, fewer ROMS processes keep up with SWAN.

Earlier result (2026-10-24, the same patch, control VM, 6 ROMS + 2 SWAN):
WEC kernel 386 -> 217 CPU-s (-44 %), largest relative difference 5e-7 after
1 h.

## Who is affected

Every coupled ROMS + SWAN (or WW3) run with the v3.9 default spectral Stokes
drift: the Stokes computation costs about a third less. Results change only
in the last bits.
