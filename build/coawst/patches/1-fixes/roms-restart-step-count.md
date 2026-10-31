# roms-restart-step-count.patch: stop a restart whose step number does not fit ROMS's step counter

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | only when `(time - DSTART)/DT + 1` does not fit a 4-byte integer (or is below 1): a perfect restart then stops with a message instead of continuing wrongly; other runs start the step counter at 1 with a warning, instead of a garbage value. Everything else is unchanged, bit for bit |
| **Default** | on |
| **Files** | `ROMS/Utility/get_state.F` (`step_count`) |
| **Evidence** | Reef_Ideal_A15 with `DSTART` 730119 days before its start: before the patch, output on the wrong steps and the restarted run ends at 2352 s instead of 3600 s; after, the restart stops with the message and the fresh runs equal the normal case bit for bit; the normal case is bit-identical before and after |
| **Test** | [`tests/fixes/roms-restart-step-count/run.sh`](../../../../tests/fixes/roms-restart-step-count/run.sh), see its [README](../../../../tests/fixes/roms-restart-step-count/README.md) |
| **Upstream** | not reported yet |

## In short

ROMS numbers its time steps from the date `DSTART` (days since `TIME_REF`):
the first step of a run is `ntstart = NINT((time - DSTART)/DT) + 1`, where
`time` is the time of the initial or restart record. The counter is a
4-byte integer (at most 2,147,483,647). If an initial file is dated in
calendar time, say 2000-01-01, and `DSTART` is left at 0 with `TIME_REF = 0`,
the time is about 730,000 days after `DSTART`, and the step number (1.6e10
at a 4 s step) does not fit. `NINT` then returns whatever the conversion
leaves: a negative number, which ROMS clamps to 1, or a large positive one.
Nothing reports it.

For a fresh run a counter of 1 is harmless, but a large positive counter
shifts the output schedule (output is written when the step number is a
multiple of `NHIS`). For a **perfect restart** both are wrong. ROMS expects
the counter to continue from the restart time, and a counter of 1 makes the
restarted run take its first step as a cold start (Euler, then AB2, instead
of AB3 with the restored history), so it does not continue the run exactly.
A garbage counter also loses the restart's place in the run: in the test,
the restarted run ended at 2352 s instead of 3600 s.

The patch computes the step number in double precision first. If it does
not fit, or falls before step 1:

- a perfect restart stops (`exit_flag = 2`) with
  ```
  GET_STATE - perfect restart: the step number of the restart time does not fit the step counter:
     (time - DSTART)/DT + 1 =   1.0514E+10  (time =   1.8000E+03 s, DSTART =   -730119.0000 days)
     Set DSTART (days since TIME_REF) to the start of the run, the time of the initial file.
  ```
- any other run starts the counter at 1, as it would with `DSTART` at its
  start time, and prints
  ```
  GET_STATE - warning: (time - DSTART)/DT + 1 =   1.0514E+10 does not fit the step counter; it starts at 1.
     Set DSTART to the start of the run (restarts need it).
  ```

The real fix is always in the case: set `DSTART` to the start of the run.
The patch makes the mistake visible.

## How it was found

A new test case for `swan-closed-ring` (`tests/cases/Circle_Island`, 2026-10-31)
had an initial file dated 2000-01-01 and an `ocean.in` from Reef_Ideal_A15
with `DSTART = 0`. Its restart was 4.5e-5 off. Debug prints in `pre_step3d`
and `step3d_uv` showed the restarted run counting from step 1 (with
`ntfirst = 1`, so a cold start), where the uninterrupted run was at step 451. The
step number of 2000-01-01 at 4 s steps is 1.6e10, which wrapped to a negative
number and was clamped to 1. With `DSTART = 730119` days the case restarts to
1e-11 (see `swan-closed-ring.md`).

## step_count: the change

In `get_state.F` (NetCDF and PIO readers alike), where the start step is
set:

```fortran
!  before
          ntstart(ng)=NINT((time(ng)-dstart*day2sec)/dt(ng))+1
          IF (ntstart(ng).lt.1) ntstart(ng)=1
!  after
          my_step=(time(ng)-dstart*day2sec)/dt(ng)+1.0_dp
          IF ((my_step.lt.0.5_dp).or.                                   &
     &        (my_step.ge.REAL(HUGE(ntstart(ng)),dp))) THEN
            IF (PerfectRST(ng)) THEN
              ...message...
              exit_flag=2
              RETURN
            END IF
            ...warning...
            ntstart(ng)=1
          ELSE
            ntstart(ng)=NINT((time(ng)-dstart*day2sec)/dt(ng))+1
          END IF
          IF (ntstart(ng).lt.1) ntstart(ng)=1
```

When the step number fits, the original expression is used unchanged, so
results are bit-identical. A perfect restart whose time is before `DSTART`
also stops: its counter would be clamped to 1 and the restart would start
cold.

## How the test works

`tests/fixes/roms-restart-step-count/run.sh`
([README](../../../../tests/fixes/roms-restart-step-count/README.md)) builds
Reef_Ideal_A15 before and after the patch (all fixes, plus the two
improvements A15's SWAN needs). It runs 60 min straight and 30 + 30 min
restarted (`tests/tools/restart_inside.sh`) in two variants. *normal* is the
case as it is: its initial time is 0 days and `DSTART = 0`. *far* sets
`DSTART = -730119` days, so the start is 730119 days after `DSTART`, the same
as an initial file dated 2000-01-01 with `DSTART = 0`.

## Engine test results

Run 2026-10-31 on Cloud Batch (c2d-standard-8 Spot, ROMS 1x6 + 2 SWAN). PASS.

| Variant | Before the patch | After the patch |
|---|---|---|
| far, fresh runs | step counter 1,923,779,008 (wrapped); history at 552, 1152, ... s instead of 0, 600, ... | warning printed; bit-identical to the normal case (all variables except the stored `dstart`) |
| far, restart | restarted run ends at 2352 s instead of 3600 s, no record in common with the straight run | stops at once with the message (exit 1, no history written) |
| normal, restart | restarted vs straight 4.7e-10 m/s | the same, 4.7e-10 m/s |
| normal, all runs | | bit-identical to before (ROMS history and SWAN Hs, straight, part1, part2) |

The Circle_Island case with `DSTART = 0` wrapped to a negative number
instead (1.6e10 steps), so its fresh runs were right and only its restart
was wrong: the other face of the same overflow.

## Who is affected

Runs whose initial or restart time is far from `DSTART`: initial files dated
in calendar time with `DSTART` left at 0, or `DSTART` set to the wrong
date. Perfect restarts of such runs now stop instead of continuing wrongly;
fresh runs now always start their counter at 1 and say so.
