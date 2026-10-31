# swan-periodic-fixes.patch: SWAN with periodic lateral boundaries (REPEATING)

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | yes, for SWAN with `COORDINATES ... REPEATING`: output on the computational grid (item 11), runs with several SWAN processes (item 12, crashed before), coupled periodic runs with spectral Stokes drift (item 15); non-periodic runs are unchanged bit for bit |
| **Default** | on |
| **Files** | `swanpre1.ftn` (item 11); `swanparll.ftn`, `swancom1.ftn`, `swanmain.ftn`, `swanpre3.ftn`, `waves_coupler.ftn` (item 12); `waves_coupler.ftn` (item 15) |
| **Evidence** | standalone periodic SWAN: COMPGRID output complete and on the grid points, 4 processes = 1 process (crashed before); source check of items 12 and 15 (results below) |
| **Test** | [`tests/fixes/swan-periodic-fixes/run.sh`](../../../../tests/fixes/swan-periodic-fixes/run.sh) |
| **Upstream** | not reported (SWAN's manual calls `REPEATING` "only for academic cases") |

## Background

`COORDINATES CARTESIAN REPEATING` makes SWAN's grid periodic in x: waves
leaving through the east side come back in through the west side. It is the
natural choice for an idealized coast that is uniform alongshore, or periodic
like a row of reef passes: no artificial side boundaries, where SWAN otherwise
has no incoming waves and casts a wave shadow into the domain (up to 1.2 m of
Hs in the test below). ROMS has the same option (`EWperiodic`), so in a
coupled run both models can be periodic. In COAWST v3.9 the option worked
only in the simplest case (serial SWAN, output on explicitly defined frames,
no coupling).

## Item 11: output on the computational grid missed half its points

With `REPEATING` a regular grid has MXC points at x = 0 ... XCLEN - DX (the
point at x = XCLEN is x = 0 again), but SWAN's built-in `COMPGRID` output frame
spread its MXC points over 0 ... XCLEN (spacing XCLEN/(MXC-1)). So
`BLOCK 'COMPGRID'` output was interpolated between grid points, and about half
of it came out as exception values (NaN in NetCDF). The coupler evaluates the
fields it sends to ROMS on the same frame, so a periodic coupled run would also
have sent ROMS misplaced and missing wave fields. Fix: frame length
XCLEN - DX when `REPEATING`.

## Item 12: several SWAN processes crashed on periodic grids longer in x than in y

SWAN cuts its grid into strips across the longer side, x-strips if
MXC > MYC. Its halo exchange and sweep pipeline never wrap around in x, so
with `REPEATING` the strips at the seam got no neighbour data: a segfault in
`SWRECVAC` on the first step, or (once) a run that finished with Hs below
0.02 m everywhere. y-strips are fine, since each process then holds the whole
period. Fix: with `REPEATING`, always cut into y-strips. The direction is
decided at 22 places (partitioner, block administration, sweep pipeline,
output collection, nesting, COAWST's coupler); each test `MXC > MYC` gets
`.AND. KREPTX .EQ. 0`.

## Item 15: in coupled periodic runs the spectral Stokes fields reached ROMS shifted

With `REPEATING` the coupling layout has one column more per row than SWAN's
grid (ROMS's i = 0 ... Lm+1 against SWAN's MXC columns), and the ordinary wave
fields (Hs, period, dissipation, ...) are re-indexed for that. The spectral
fields that ROMS's `SPECTRUM_STOKES` uses (`KSS`, `USS`, `VSS`, one per
frequency) were still taken as in the non-periodic layout, so row j came out
shifted by j - 1 columns. In the first coupled periodic run of the idealized
reef case A15 (2026-10-21), the deep pass's spectra landed on the 0.5 m deep
crest, the Stokes drift there reached 1.4 m/s (0.1 m/s in the non-periodic
run), and ROMS blew up after 35 minutes. Fix: build an index map (`isrc`)
alongside the ordinary fields and take the spectra through it. Non-periodic
runs use the same indices as before.

## Test

`tests/fixes/swan-periodic-fixes/run.sh SOURCE OUTDIR`:

1. **Source check** (`check_source.py`): every x-strip test excludes periodic
   grids (item 12); the spectral Stokes fields go through `isrc` (item 15).
2. **Standalone SWAN** (`tests/cases/Swan_Periodic_Test`, inputs from
   `make_inputs.py`): an A15-like reef with one pass (A15's cross-shore
   profile, `a15_profile.txt`), periodic in x, waves Hs 1 m, Tp 10 s from
   20 deg east of north, 1 h. Grid `wide` (4 km, 200 x 121 points: x-strips
   before the patch) and `tall` (2 km, 100 x 121: y-strips, the control), each
   with 1 and 4 SWAN processes. Checks: 4 processes give the 1-process Hs
   (item 12); `COMPGRID` output equals output on a frame on the grid points,
   none missing (item 11).

Item 15 shows only in a coupled periodic run. A15, where it was found, has a
curvilinear SWAN grid, and periodic curvilinear grids come with
`2-improvements/swan-periodic-curvilinear.patch`; the coupled run is part of
that patch's test.

## Engine test results

Run 2026-10-30/31 on the control VM; "before" is the series up to this patch
(so it already has the output fixes), "after" adds it. PASS:

```
== 1. source check
before: item 12  x-strip tests (MXC > MYC): 22, without KREPTX.EQ.0: 22   BAD
        item 15  spectral Stokes fields taken through: ['points']         BAD
after:  item 12  ... without KREPTX.EQ.0: 0                               ok
        item 15  ... taken through: ['isrc']                              ok
== 2. standalone periodic SWAN, Hs after 1 h
before: item 12  wide (x-strips): 4 vs 1 processes  max |diff| 1.35 m,
                 Hs max 0.0198 m (the 4-process run is garbage)           BAD
        item 12  tall (y-strips, control): 4 vs 1   bit-identical         ok
        item 11  wide: COMPGRID vs grid points      0 missing, values differ BAD
        item 11  tall: COMPGRID vs grid points      0 missing, values differ BAD
after:  item 12  wide: 4 vs 1 processes             bit-identical         ok
        item 12  tall: 4 vs 1 processes             bit-identical         ok
        item 11  wide, tall: COMPGRID vs grid points  identical, 0 missing  ok
```

Item 12 before: the 4-process run on the x-strip grid did not crash this time
but produced Hs below 0.02 m everywhere (the 1-process run reaches 1.4 m),
the second failure mode seen in the earlier tests. Item 11 before: COMPGRID
output was off by up to 0.24 m (wide) and 0.25 m (tall) against the output on
the grid points, being interpolated between them; no point was missing in
this run. In the earlier tests (before the output fixes) about half were
missing; that part was most likely the uninitialised output flags of
`swan-output-fixes` (item 14), which this series fixes first.

## Earlier results (2026-10-21, same changes, more cases)

| Check | stock SWAN | patched |
|---|---|---|
| pass across the seam vs pass in the middle shifted by half a period, 1 process | 3e-5 m | same |
| 4 vs 1 process, periodic, y-strips | identical | identical |
| 4 vs 1 process, periodic, x-strips | segfault in `SWRECVAC` (once: Hs < 0.02 m everywhere) | identical |
| `BLOCK 'COMPGRID'` output, periodic | about half missing, rest interpolated | equals output on the grid points |
| non-periodic vs periodic | up to 1.2 m Hs difference near the upwave side | same |

Non-periodic runs and the serial periodic computation are unchanged by the
patch, bit for bit. The seam residual (at most 3e-5 m, in the lagoon) is at
the level of SWAN's iteration error: one sweep per time step does not converge
exactly where the sweep order meets the seam.

## Limits

Not periodic, as before: SWAN's own `SETUP` and `DIFFRACTION`, and obstacles
across the seam. Curvilinear periodic grids: the improvement
`swan-periodic-curvilinear`.
