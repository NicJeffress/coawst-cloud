# roms-vandera-no-sand.patch: van der A output without sand is zero, not unset memory

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | output only, and only with `BEDLOAD_VANDERA` and no sand class (`NNS = 0`): the van der A fields are written as zero instead of whatever was in memory; the model state is unchanged; runs with sand are bit-identical |
| **Default** | on |
| **Files** | `ROMS/Nonlinear/Sediment/sed_bedload_vandera.F` (one block) |
| **Evidence** | Inlet_test DiffGrid (mud only), built with unset memory filled with NaN: `fd_wbl` NaN at every water point before, zero after, every other field bit-identical; Inlet_test Coupled (sand) bit-identical |
| **Test** | [`tests/fixes/roms-vandera-no-sand/run.sh`](../../../../tests/fixes/roms-vandera-no-sand/run.sh), see its [README](../../../../tests/fixes/roms-vandera-no-sand/README.md) |
| **Upstream** | not yet reported to COAWST |

## In short

The van der A bedload scheme (`BEDLOAD_VANDERA`) computes its quantities in
a loop over the sand classes. The routine then copies eight of them into
fields that ROMS writes to the history file: the friction factor from
currents `fd_wbl` and the wave-shape diagnostics (Ursell number, velocity
and acceleration skewness, crest and trough velocities and periods). In a
case without sand, such as COAWST's Inlet_test DiffGrid and Refined (mud
only), the loop never runs, the local arrays are never set, and the copies
write whatever was in each process's memory. The fix sets those local
arrays to zero before the loop. Where there is sand the loop overwrites them
before the copy, so nothing changes.

## Background

`sed_bedload_vandera.F` computes bedload of non-cohesive sediment (sand)
from the wave shape and the current, after van der A et al. (2013). Bedload
applies to sand only, so the work is done in

```fortran
      DO ised=NCS+1,NST          ! sand classes (NCS mud classes come first)
        ...
        DO j=...; DO i=...
          ...
          CALL full_wave_cycle_stress_factors(..., fd_wbll(i,j), ...)
```

with the results held in tile-local arrays (`fd_wbll`, `ursell_nol`,
`RR_asymwavel`, `beta_asymwavel`, `ucrest_rl`, `utrough_rl`, `T_crestl`,
`T_troughl`, and `ksd_wbll`). After the loop, the routine copies them to the
global fields that the output routines write:

```fortran
      DO j=Jstr,Jend
        DO i=Istr,Iend
          ursell_no(i,j)=ursell_nol(i,j)
          ...
          bottom(i,j,idfdw)=fd_wbll(i,j)
```

## The bug

With mud only (`NCS = 1`, `NNS = 0`, so `NST = 1`), the sand loop runs from 2
to 1: zero times. The copy still runs, and the local arrays, which are
automatic arrays on each process's stack, hold leftovers from earlier
calls. The written fields are therefore meaningless, and differ between
builds, between processes and between runs:

- In COAWST's Inlet_test DiffGrid (stock, ROMS 2x2 + 2 SWAN, 2 h), `fd_wbl`
  held values from -0.8 to 1e37, with 1854 negative water points. The
  friction factor (`fd_calc_madsen`) can only be 0 or at least 1e-14.
- The values changed abruptly at the edge between two tiles (about 1e-17 on
  one side, 1e-7 on the other): two MPI processes with different leftovers.
- Two builds of the same active code wrote different `fd_wbl` (e.g. 5.69 vs
  0 in one column), which is how the examples sweep
  ([tests/examples](../../../../tests/examples/README.md)) found it.
- With unset local memory filled with NaN (`-finit-real=snan`), `fd_wbl`
  was NaN at all 5333 water points, and was the only NaN field.

The model state does not depend on these fields: they are only written to
files (with `BEDLOAD_VANDERA_DIRECT_UDELTA`, `ksd_wbll` is copied to
`bottom(:,:,idksd)`, which is likewise not read back). Every other field of
the runs above is bit-identical between builds.

## The fix

Set the nine local arrays to zero with the routine's other initialisations,
before the loop:

```fortran
       FE_r=0.0_r8
       fd=0.0_r8
 !
+!  The local arrays below are set in the loop over sand classes
+!  (ised=NCS+1,NST) and copied to output fields after it. Start them
+!  at zero, so that a case without sand (NNS=0) writes zeros, not
+!  unset memory.
+!
+      ursell_nol=0.0_r8
+      RR_asymwavel=0.0_r8
+      beta_asymwavel=0.0_r8
+      ksd_wbll=0.0_r8
+      fd_wbll=0.0_r8
+      ucrest_rl=0.0_r8
+      utrough_rl=0.0_r8
+      T_crestl=0.0_r8
+      T_troughl=0.0_r8
```

Zero is what "no bedload" means for these quantities. With sand, the loop
sets every point from `Istrm1` to `Iendp1` (wider with `SED_WENO`), which
covers the copied range `Istr` to `Iend`, so the zeros are always
overwritten and results are bit-identical. The cost is nine tile-sized
array assignments per step, negligible next to the bedload computation.

## When it matters

Only for the output of runs with `BEDLOAD_VANDERA` and mud only: the van der
A fields in the history (and average) files were garbage and are now zero.
Anyone who plotted or averaged `fd_wbl` or the wave-shape fields from such a
run should not trust them. Runs with at least one sand class, and every
model field of every run, are unchanged.

With more than one sand class the arrays hold the last class's values; that
is COAWST's design and the patch does not change it.

## How the test works

[`tests/fixes/roms-vandera-no-sand/run.sh`](../../../../tests/fixes/roms-vandera-no-sand/run.sh)
builds, before and after the patch:

- Inlet_test DiffGrid (mud only) with `ROMS_FFLAGS_EXTRA="-finit-real=snan"`,
  so unset local memory is NaN rather than leftovers that change from build
  to build;
- Inlet_test Coupled (sand), with the usual flags.

It runs each for 2 simulated hours and checks: DiffGrid before has NaN in
`fd_wbl`; DiffGrid after has `fd_wbl` (and any other van der A field written)
equal to zero, and every other variable bit-identical to before; Inlet_test
Coupled is bit-identical before and after in every variable.

## Results

Run 2026-11-02 on the control VM (4 vCPUs), engine build settings, 2
simulated hours (`run.sh OUTDIR`):

| Check | Result |
|---|---|
| DiffGrid before: `fd_wbl` unset | NaN at 10666 of 15999 water values: every water point of the two records after the start (the initial record is written before the bedload routine first runs) |
| DiffGrid after: `fd_wbl` zero | 0 NaN, largest value 0 |
| DiffGrid: other variables before vs after | 193 compared, all bit-identical |
| Inlet_test Coupled (sand) before vs after | 211 compared (`fd_wbl` among them), all bit-identical |

**PASS.** Of the other van der A fields, the DiffGrid history file holds only
`fd_wbl` (the wave-shape fields are requested in its input but not written in
this configuration).

## Limits

- The test uses the NaN fill to make "unset" visible; a normal build writes
  arbitrary values instead, which no test can predict.
- Upstream COAWST might prefer to skip the copy, or the van der A
  computations entirely, when there is no sand; zeros are the smallest change
  that makes the output well defined.
