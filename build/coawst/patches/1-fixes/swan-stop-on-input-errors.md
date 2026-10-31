# swan-stop-on-input-errors.patch: stop the coupled run when SWAN's input has errors

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | no (run control: a run that used to carry on after a SWAN input error now stops) |
| **Default** | on (`SET MAXERR` in the SWAN input still lets a user accept errors on purpose) |
| **Files** | `SWAN/src/waves_control.ftn` (`stop_on_input_errors`) |
| **Evidence** | Inlet_test with an output request SWAN refuses: stock carries on and goes out of bounds; patched stops with a message |
| **Test** | [`tests/fixes/swan-stop-on-input-errors/run.sh`](../../../../tests/fixes/swan-stop-on-input-errors/run.sh), see its [README](../../../../tests/fixes/swan-stop-on-input-errors/README.md) |
| **Upstream** | not yet reported to COAWST |

## In short

When SWAN finds errors in its input file, standalone SWAN refuses to run. In
COAWST it said so in its PRINT file and then ran anyway: the coupled run
carried on with SWAN half set up. Depending on the error, that meant writing
out of bounds, sending ROMS meaningless wave fields, or crashing much later
with no hint of the cause. The fix makes the whole run stop at once with a
message pointing to the PRINT file, which now actually contains SWAN's
explanation.

## Background: how SWAN reports input errors

SWAN reads its command file (`swan.in`) at start-up and checks each command.
Problems are reported with a level: 1 warning, 2 error, 3 severe error. SWAN
keeps the highest level so far in `LEVERR`. After reading the input it
compares `LEVERR` with `MAXERR` (default 1, changeable with `SET MAXERR`): if
the level is higher, the run must not start, and SWAN writes

```
 ** No start of computation because of error level:  2
 ** To ignore this error, change [maxerr] with the SET command
```

into its PRINT file (`PRINT`, or `PRINT01`, ... one per process). Standalone
SWAN then stops.

## The bug

In COAWST, SWAN is not a program of its own but a library called by COAWST's
master program: `waves_control.ftn` calls `SWAN_INITIALIZE`, which reads the
input. When the error level was too high, `SWAN_INITIALIZE` printed the
message and returned; nothing checked the level afterwards. The coupled run
went on into the time loop and the first coupling exchange, with SWAN's
setup incomplete.

What happens next depends on the error. With a rejected output request
(e.g. a NetCDF file for a quantity that has no NetCDF name), the output arrays
for that request were never allocated, and the first output wrote out of
bounds (`SWOEXC`), a memory corruption that may or may not crash. With other
errors, SWAN could compute with defaults the user did not intend. Meanwhile
the run looks healthy from outside: ROMS prints its progress, the job keeps
using cloud time, and the only sign is a line in a SWAN file that nobody reads
while the run is going. Worse, when the run is killed, SWAN's buffered PRINT
output is lost, so the file that would explain the problem can come out
empty.

## The fix

Right after `SWAN_INITIALIZE`, `waves_control.ftn` checks the error level. If
it is above `MAXERR`, it writes a message to the screen (the run's log),
flushes SWAN's PRINT file to disk, and stops the whole MPI job with SWAN's own
exit routine:

```fortran
        CALL SWAN_INITIALIZE (NUM_SGRIDS, MyCOMM, Wname(ng))
+!       Do not run with a SWAN setup that has input errors.
+        IF (LEVERR.GT.MAXERR .AND. MAXERR.NE.-1) THEN
+          WRITE (SCREEN,'(A,I3,A)') ' SWAN input error level',
+     &      LEVERR, ' > MAXERR: stopping, see SWAN PRINT file'
+          LEVERR = MAX(LEVERR, 4)
+          FLUSH (PRINTF)
+          CALL SWEXITMPI
+        END IF
```

(`OCPCOMM4` now also exports `PRINTF`, `LEVERR` and `MAXERR` to this routine.)
`LEVERR` is raised to 4 because `SWEXITMPI` (`swanparll.ftn`) calls
`MPI_ABORT`, which stops every process of the job including ROMS's, only for
`LEVERR >= 4`; below that it calls `MPI_FINALIZE`, which would leave ROMS
waiting for SWAN at the next coupling exchange. `SET MAXERR` in the SWAN input still raises the threshold for a user
who wants to run despite warnings or errors.

In this repository the stop has already paid for itself: twice while writing
the tests it stopped runs whose SWAN input had a mistake (a NetCDF quantity not
yet supported, and quadruplet interactions without wind) at the first second,
with SWAN's explanation in the PRINT file.

## How the test works

`tests/fixes/swan-stop-on-input-errors/run.sh` ([README](../../../../tests/fixes/swan-stop-on-input-errors/README.md))
runs stock Inlet_test with one extra output request that stock SWAN rejects
(`BLOCK ... 'wdirbot.nc' ... DIRBOT`: DIRBOT has no NetCDF name in stock
SWAN, error level 2), before and after the patch. SWAN is built with
`-fcheck=bounds` so that the out-of-bounds write of the "before" run stops
the run visibly instead of passing silently:

- before: "No start of computation" in the PRINT file, but the run carries on
  and the first output goes out of bounds (run-time error in `swanout1`);
- after: the job stops at once with `SWAN input error level  2 > MAXERR`, with
  no run-time error, and the PRINT file contains SWAN's message ("netCDF
  output not allowed for wdirbot.nc").

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

`voq` is SWAN's array of output values; "upper bound of 0" means it was never
allocated for the rejected request, and the "before" run wrote into it anyway.

## Who is affected

Every coupled run whose SWAN input has an error above `MAXERR`: before this
fix it ran on in an undefined state instead of stopping.
