# Test: swan-halo-hang

Checks [`1-fixes/swan-halo-hang.patch`](../../../build/coawst/patches/1-fixes/swan-halo-hang.md):
SWAN's halo exchange must not deadlock when a halo row is longer than MPI's
eager limit.

## The idea

The bug is a deadlock that appears only when the rows SWAN processes
exchange are longer than about 1024 values (4 kB, OpenMPI's eager limit in
shared memory). So make a grid whose exchanged rows are just above that
(1100 points) and one just below (650 points), run each on 2 processes, and
see which ones finish. A hung run is stopped by a timeout.

## What it does, step by step

1. Builds `tests/cases/Swan_Periodic_Test` (standalone SWAN) before and after
   the patch.
2. `make_inputs.py` writes a periodic channel: flat 10 m bottom, 31 points
   cross-shore, MXC points alongshore (20 m mesh), waves from the north,
   10 simulated minutes. Periodic grids are always cut into y-strips, so two
   processes exchange whole rows of MXC points.
3. Runs, with a timeout (default 600 s):

   | Run | Row length | Expected |
   |---|---|---|
   | before, 1100 points, 2 processes | 4.4 kB | hangs: stopped by the timeout |
   | before, 650 points, 2 processes (control) | 2.6 kB | finishes |
   | after, 1100 points, 2 processes | 4.4 kB | finishes |
   | after, 1100 points, 1 process | | finishes |

4. Compares Hs of the two "after" runs: 2 processes must equal 1 process bit
   for bit (the new exchange moves the same data).

A hung run uses 100 % of its CPUs until the timeout; the test kills its
container afterwards.

## Running it

```bash
PYTHON=~/venv/bin/python tests/fixes/swan-halo-hang/run.sh OUTDIR [TIMEOUT_S]
```

About 15 min (most of it the timeout).

## Reading the output

```
   before-1100-np2    1100 points, np 2: HUNG after 600 s
   before-650-np2      650 points, np 2: finished after 17 s
   after-1100-np2     1100 points, np 2: finished after 28 s
   after-1100-np1     1100 points, np 1: finished after 51 s
   np1 vs np2: ALL BIT-IDENTICAL
PASS
```

## Last result

2026-10-31, control VM (OpenMPI 4, shared memory): PASS.
