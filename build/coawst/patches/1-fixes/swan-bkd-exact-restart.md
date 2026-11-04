# swan-bkd-exact-restart.patch: BKD breaking restarts exactly

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | restarts with `BREAKING BKD` only (now exact). Runs without restarts are unchanged, apart from one new line in `PRINT` |
| **Default** | on |
| **Files** | `swancom1.ftn`, `swanmain.ftn`, `swanpre1.ftn` |
| **Evidence** | coupled idealized reef: 1e-7 m/s off an hour after a restart before, bit-identical after, over three segments |
| **Test** | [`tests/fixes/swan-bkd-exact-restart`](../../../../tests/fixes/swan-bkd-exact-restart/README.md) |
| **Upstream** | not reported |

## What was wrong

SWAN's `BKD` breaker index (Salmon et al. 2015) is stored in `COMPDA(:,JGAMMA)`,
which the exact restart file holds. Whether that index may still change is held
by a logical `MODGAM` in module `SWCOMM3`, which the file did not hold.

`MODGAM` is a one-way switch. It starts true, and the index is updated. At the
end of an iteration, the first time the accuracy reaches `NPNTS` (95 %, an
undocumented `BKD` argument), it becomes false and stays false:

```fortran
IF (MODGAM .AND. ACCUR.GE.PNUMS(37)) MODGAM = .FALSE.
```

A restarted program starts with `MODGAM` true again, so it recomputes the index
at the restart once, where the uninterrupted run kept the frozen one. That gives
a small, growing difference from the first exchange after the restart.

## The change

- `SWAN_RST_POST` writes `MODGAM` as one more record, after the post-exchange `COMPDA`.
- `INITVA` reads it when present. Older files have no such record and behave as before.
- When `MODGAM` turns false, SWAN writes `BKD breaker index frozen at <time> accuracy <value>` to `PRINT`.

## How it was found

Restarts were bit-identical until `BKD` became the default breaking. A 2 h pair
with a restart at 1 h and history every minute, varying one setting at a time,
was bit-identical with `CON` and differed with `BKD` whatever else was set. The
first difference came at the first exchange after the restart.

## Limits and a note on the freeze itself

This patch does not change the freeze: it makes the restart reproduce it. In
every non-stationary run, including coupled runs, the index freezes for the
rest of the run as soon as the accuracy first reaches `NPNTS`: at 50 min in the
idealized reef at DT 3 s, just after a 30 min wave ramp. Tide and wave changes
after that do not reach the index. Where kD is below about 1 the index depends
only on the bed slope, so it should not change there anyway; see the case's
notebook for a run with the freeze removed.

This patch is a plain diff, not produced by `generators/make_swan_patches.py`.
