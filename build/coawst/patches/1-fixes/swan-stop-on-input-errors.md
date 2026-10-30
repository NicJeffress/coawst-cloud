# swan-stop-on-input-errors.patch: stop the coupled run when SWAN's input has errors

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no (run control: a run that used to carry on after a SWAN input error now stops) |
| **Default** | on (`SET MAXERR` in the SWAN input still lets a user accept errors on purpose) |
| **Files** | `SWAN/src/waves_control.ftn` (item 5) |
| **Evidence** | Inlet_test with an output request SWAN refuses: stock carries on and goes out of bounds; patched stops with a message (results below) |
| **Test** | [`tests/fixes/swan-stop-on-input-errors/run.sh`](../../../../tests/fixes/swan-stop-on-input-errors/run.sh) |
| **Upstream** | not yet reported to COAWST |

## Summary

When SWAN finds errors in its input file, it records an error level
(`LEVERR`: 1 warning, 2 error, 3 severe) and, if that is above `MAXERR`
(default 1), refuses to compute: it prints "No start of computation" in its
PRINT file. Standalone SWAN then stops. In COAWST, `SWAN_INITIALIZE` returned
anyway and the coupled run carried on: into the time loop and the first
coupling exchange, with SWAN half set up. What happens then depends on the
error. With a refused output request, the output arrays for that request
were never allocated and the first output wrote out of bounds (`SWOEXC`).
In general, a coupled run could go on for hours with the wave model in an
undefined state, and the only sign was a line in a file nobody reads while
the run looks healthy.

## The fix

Right after `SWAN_INITIALIZE`, check the error level. If it is above
`MAXERR`, write a message to the screen (the run's log), flush SWAN's PRINT
file (otherwise the abort loses its buffered contents, and the file that says
what was wrong comes out empty), and stop the whole MPI job with SWAN's own
exit routine:

```fortran
!       Do not run with a SWAN setup that has input errors.
        IF (LEVERR.GT.MAXERR .AND. MAXERR.NE.-1) THEN
          WRITE (SCREEN,'(A,I3,A)') ' SWAN input error level',
     &      LEVERR, ' > MAXERR: stopping, see SWAN PRINT file'
          LEVERR = MAX(LEVERR, 4)
          FLUSH (PRINTF)
          CALL SWEXITMPI
        END IF
```

`SET MAXERR` in the SWAN input still raises the threshold for a user who
wants to run despite warnings or errors.

## Test

`tests/fixes/swan-stop-on-input-errors/run.sh` runs stock Inlet_test with
one extra output request that stock SWAN refuses (`BLOCK ... 'wdirbot.nc'
... DIRBOT`: DIRBOT has no NetCDF name in stock SWAN, error level 2), before
and after the patch, with SWAN's run-time checks on (`-fcheck=bounds`) so an
out-of-bounds access shows instead of passing silently:

- before: "No start of computation", the run carries on, and the first output
  goes out of bounds (run-time error in `swanout1`);
- after: the job stops at once with `SWAN input error level  2 > MAXERR`, no
  run-time error, and the PRINT file contains SWAN's message ("netCDF output
  not allowed for wdirbot.nc").

## Engine test results

Run 2026-10-30 on the control VM, stock Inlet_test with the `wdirbot.nc`
request, 1 h, SWAN built with `-fcheck=bounds`; "before" is the series up to
this patch, "after" adds it. PASS:

```
before  SWAN refuses the input but the run carries on                ok
before  and goes out of bounds                                       ok
        (At line 945 of file .../swanout1.f: Index '1' of dimension 1 of
         array 'voq' above upper bound of 0)
after   stops: SWAN input error level 2 > MAXERR                     ok
        ( SWAN input error level  2 > MAXERR: stopping, see SWAN PRINT file)
after   no run-time error                                            ok
after   PRINT file says what was wrong                               ok
        ( ** Error : netCDF output not allowed for wdirbot.nc)
```
