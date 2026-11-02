# Test: ROMSPath on a periodic channel

Checks the ROMSPath fork that [`build/romspath`](../../../build/romspath/README.md)
builds, commit by commit, against an exact answer.

## The idea

A channel that is periodic in xi (a ROMS `EW_PERIODIC` grid) carries uniform
flow along xi that changes from record to record: u = U0 + dU × record, with
records every dt. ROMSPath interpolates the flow in time between records, so a
particle released at t = 0 has moved

    s(t) = U0 t + dU t² / (2 dt)

along the channel, wherever it is. Because the flow is uniform in space,
every particle should match s(t) to the output precision. That makes errors in
record timing, Runge-Kutta stage times and seam crossings stand out:

- a particle that crosses the seam must not jump;
- a particle one record behind loses dU × dt × (number of records);
- a particle released on a rotated grid must start in the right cell.

The defaults: 40 × 10 cells of 10 m (period 400 m), 4 levels, 10 m deep, U0 =
0.05 m/s, dU = 0.01 m/s per 10-minute record, 2 h, internal step 10 s, no
turbulence. Ten particles along the channel at mid-depth, so they reach the
seam at different times; each travels 792 m in 2 h (u grows from 0.05 to 0.17
m/s), so it crosses the seam about twice.

## What it does, step by step

1. Clones the fork (or uses `ROMSPATH_SOURCE`) at `REF`, the commit pinned in
   the Dockerfile, and builds the image and the build-stage image
   (`build/romspath/build.sh`).
2. [`make_hydro.py`](make_hydro.py) writes the channel twice: grid lines along
   x and y, and the same grid rotated by 30 degrees (`--angle 30`).
   [`make_input.py`](make_input.py) writes `ROMSPath.data` from the one that
   ships with ROMSPath (keys replaced, `PeriodicBoundary_X = .TRUE.` added) and
   the seed file.
3. Compiles every commit after upstream (`UPSTREAM..REF`) with its own
   makefile, and runs each on both channels; then runs the image.
4. [`check.py`](check.py) compares the particles with the exact answer: along
   the channel (modulo the period, so a particle is compared after the same
   number of crossings) and across it (which must stay zero).

Upstream itself is not run: without `PeriodicBoundary_X` it has no periodic
grids, and its namelist rejects the key.

## Running it

```bash
PYTHON=~/venv/bin/python tests/romspath/periodic-channel/run.sh OUTDIR
```

About a minute on 4 vCPUs. Needs Docker and Python with numpy and netCDF4.
`ROMSPATH_SOURCE=DIR` tests a local checkout instead of GitHub.

## Last result

Run 2026-11-02 on the control VM (local checkout of the fork, `REF` = its
README commit). Signed error along the channel of the worst particle, m:

| Build | straight 1 h | 2 h | rotated 1 h | 2 h |
|---|---|---|---|---|
| Periodic boundaries (first commit) | -21.75 | -48.05 | -14.18 | -40.48 |
| + periodic wrap by the ROMS period | -21.75 | -58.05 | -24.18 | -60.48 |
| + position to grid index on curvilinear grids | -21.75 | -58.05 | -21.75 | -58.05 |
| + record counter | -0.80 | -1.10 | -0.80 | -1.10 |
| + RK4 fourth stage, spline end weights, timers | -0.80 | -1.10 | -0.80 | -1.10 |
| + first external step | -0.30 | -0.60 | -0.30 | -0.60 |
| + RK4 stage times (last code commit) | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| image (`-O3 -march=x86-64-v3`) | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

**PASS.** How to read it:

- **First commit.** The record counter dominates: one record behind from 20
  minutes on costs dU × 6000 s = -60 m by 2 h. The first commit looks better
  than the second because its seam jump (+10 m per crossing) hides part of
  that.
- **Rotated grid.** Before the curvilinear fix it starts particles in the
  wrong place, so it differs from the straight grid. After the fix the two
  grids agree exactly.
- **What this test cannot see.** Three commits leave it unchanged, as
  expected:
  - the RK4 fourth-stage position matters only where the flow varies in space;
  - the spline weights matter only with vertical turbulence;
  - the timer change affects speed only.

## Limits

- Uniform flow tests timing and seams, not spatial interpolation, turbulence
  or behaviour.
- Positions are written as 32-bit floats: "0.0000" means within about 1e-5 m
  over a 400 m channel.
