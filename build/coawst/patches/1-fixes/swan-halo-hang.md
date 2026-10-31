# swan-halo-hang.patch: SWAN hung in its halo exchange once a row exceeded MPI's eager limit

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no (a deadlock fix: the data exchanged and their order are unchanged) |
| **Default** | on |
| **Files** | `SWAN/src/swanparll.ftn` (`SWEXCHG`, the wavefront version COAWST builds; item 20) |
| **Evidence** | periodic channel with 1100-point rows on 2 SWAN processes: stock hangs, patched finishes and equals 1 process (results below) |
| **Test** | [`tests/fixes/swan-halo-hang/run.sh`](../../../../tests/fixes/swan-halo-hang/run.sh) |
| **Upstream** | a SWAN 41.51 bug; not reported |

## Summary

When SWAN runs on several MPI processes, each holds a strip of the grid and,
after each sweep, sends its edge row ("halo") to its neighbours and receives
theirs. `SWEXCHG` did this by first sending to every neighbour with a
blocking `MPI_SEND`, and only then receiving.

That works only while MPI can buffer the whole message without waiting for
the receiver: below MPI's "eager limit". OpenMPI's shared-memory transport
buffers messages up to 4 KB (1024 single-precision values). Above that,
`MPI_SEND` waits until the matching receive is posted. Every process is then
waiting in its send for a neighbour that is itself waiting in its send: a
deadlock. SWAN sits at 100 % CPU forever. In a coupled run ROMS carries on
alone until it waits for the next wave exchange, which never comes.

It is size dependent, which made it look mysterious: grids whose strip edges
are up to 1024 points run fine; it was found on an island ring grid with
2704-point rows (a 944-point version of the same grid had run).

Diagnosed with gdb on the stuck processes (all in `SWSENDNB` called from
`SWEXCHG`) and confirmed by running the unpatched code with OpenMPI's eager
limit raised (`OMPI_MCA_btl_vader_eager_limit=65536`), which made it run.

## The fix

`SWEXCHG` now posts every receive first (`MPI_IRECV`), then every send
(`MPI_ISEND`), and waits for all of them (`MPI_WAITALL`), with separate send
and receive buffers per neighbour. This cannot deadlock at any message size.
The values exchanged and the order in which they are used are unchanged.
SWAN's sweep pipeline (`SWSENDAC`/`SWRECVAC`) passes data one way only and
cannot deadlock, so it is not changed.

## Test

`tests/fixes/swan-halo-hang/run.sh` runs standalone SWAN on a periodic
channel (`make_inputs.py`: flat 10 m bottom, 31 points cross-shore, waves
from the north, 10 simulated minutes). With `REPEATING`, SWAN cuts the grid
into y-strips, so 2 processes exchange whole rows of the grid:

| Run | Row length | Before | After |
|---|---|---|---|
| 1100 x 31 points, 2 processes | 4.4 kB | hangs (stopped by the test's timeout) | finishes |
| 650 x 31 points, 2 processes (control) | 2.6 kB | finishes | |
| 1100 x 31, 1 process | | | finishes, same Hs as 2 processes |

## Engine test results

Run 2026-10-31 on the control VM (OpenMPI 4, shared memory); "before" is
the series up to this patch, "after" adds it. PASS:

```
before-1100-np2   1100 points, np 2: HUNG after 600 s (stopped by the test)
before-650-np2     650 points, np 2: finished after 17 s
after-1100-np2    1100 points, np 2: finished after 28 s
after-1100-np1    1100 points, np 1: finished after 51 s
np1 vs np2: hs  ALL BIT-IDENTICAL
```

## Who is affected

Any SWAN run on several processes whose strips have edges longer than about
1024 points (OpenMPI in shared memory; other transports and MPI libraries
have other limits): large grids, and periodic grids, which are always cut into
y-strips, so their full rows are exchanged.
