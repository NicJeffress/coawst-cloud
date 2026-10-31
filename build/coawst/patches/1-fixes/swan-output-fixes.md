# swan-output-fixes.patch: SWAN output at the wrong place, or missing

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | output only: what is written changes, the wave computation does not |
| **Default** | on |
| **Files** | `SWAN/src/swanparll.ftn` (`table_nc_coordinates`), `SWAN/src/swanout2.ftn` (`compgrid_nc_coordinates`), `SWAN/src/swanout1.ftn` (`output_obstacle_flags`) |
| **Evidence** | Inlet_test with extra output requests: three checks bad before, all ok after |
| **Test** | [`tests/fixes/swan-output-fixes/run.sh`](../../../../tests/fixes/swan-output-fixes/run.sh), see its [README](../../../../tests/fixes/swan-output-fixes/README.md) |
| **Upstream** | `table_nc_coordinates` is in SWAN 41.51 itself; none reported yet |

## In short

Three independent bugs in how SWAN writes its results. None changes the
computed waves, but each makes output files wrong in ways that are easy to
miss, and one depends on the number of processors:

| Change | What was wrong | What you would see |
|---|---|---|
| `table_nc_coordinates` | NetCDF `TABLE` output from several SWAN processes wrote the coordinates of the first grid cells as the locations of the output points | every output point plotted at the grid origin (x = 0, 200, 400 m ...), with correct values |
| `compgrid_nc_coordinates` | `BLOCK` output on the computational grid from one SWAN process wrote x, y = -1e10 at inactive (land) points | land points plotted 10 million km away; the coordinate arrays differ between 1 and several processes |
| `output_obstacle_flags` | flags that tell SWAN whether an obstacle lies between an output point and a grid corner were never set | values between grid points missing (-9 for Hs) at random, differently from run to run |

## Background: how SWAN writes output

SWAN computes on its computational grid (`CGRID`). Output requests in the
input file name a set of locations and the quantities wanted there:

- `BLOCK 'COMPGRID' ...` writes fields on the computational grid itself (the
  output the coupler also uses, internally);
- `FRAME`, `CURVE`, `POINTS` define other sets of locations (a regular grid,
  a line, a list of points), written with `BLOCK` (fields) or `TABLE`
  (columns per point);
- the file name decides the format: `.mat` (MATLAB), `.nc` (NetCDF), text.

For locations between grid points, SWAN interpolates from the four surrounding
grid corners (`SWIPOL`), leaving out any corner that an obstacle (a
breakwater, defined with `OBSTACLE`) separates from the point.

With several SWAN processes, each computes a strip of the grid and writes its
part of each output; the parts are then collected (`SWCOLOUT`, `SWCOLBLK`)
into one file. So the same request goes through different code with one
process than with several, and both paths must write the same file.

## table_nc_coordinates: TABLE points at the grid origin

With several processes, `SWCOLBLK` merges the per-process pieces of a table.
For NetCDF tables it wrote the x and y of the output locations from
`XGRDGL`, `YGRDGL`, the coordinates of the global computational grid, starting
at its first cells, instead of the coordinates of the output points. So all
points of a `TABLE ... .nc` came out at (0, 0), (200, 0), (400, 0) ... in
Inlet_test, whatever their real location; the data values themselves were
right. An upstream SWAN 41.51 bug.

**The fix** passes the output points' coordinates `XP`, `YP` from `SWCOLOUT`
to `SWCOLBLK` (three call sites and the routine's arguments), which uses them
for tables:

```fortran
-!NCF                IF (OPTG.NE.5) THEN
+!NCF                IF (RTYPE.EQ.'TABC') THEN
+!NCF!                  TABLE: locations of the output points
+!NCF                  CALL swn_outnc_openblockfile(FILENM, MYK, MXK,
+!NCF     &                                         OVLNAM, XP, YP,
+!NCF     &                                         OQI, OQR, IVTYP, IRQ)
+!NCF                ELSE IF (OPTG.NE.5) THEN
```

(The `!NCF` prefix marks lines that SWAN's build switches on when it is
compiled with NetCDF.)

## compgrid_nc_coordinates: -1e10 coordinates with one process

With one process, `BLOCK 'COMPGRID' ... .nc` took the `x`, `y` variables of
the file from SWAN's `XP`, `YP` output quantities. Those are set to the
exception value (-1e10) at inactive points: land, or wherever the bottom has
the exception value (211 points in Inlet_test). With several processes the
same request goes through `SWCOLBLK`, which writes the grid coordinates. So
the coordinate arrays depended on the number of processes, and in the
one-process file the land points sat 1e10 m away, which breaks plotting and
interpolation.

**The fix** writes the grid coordinates in the one-process case too, whenever
the output is the computational grid itself:

```fortran
+!NCF        IF (PSNAME.EQ.'COMPGRID' .AND. OPTG.NE.5 .AND.
+!NCF     &      MXK.EQ.MXC .AND. MYK.EQ.MYC) THEN
+!NCF!         grid coordinates, also at inactive points
+!NCF          CALL swn_outnc_openblockfile(FILENM, MYK, MXK,
+!NCF     &                                 OVLNAM, XCGRID+XOFFS,
+!NCF     &                                 YCGRID+YOFFS,
+!NCF     &                                 OQI, OQR, IVTYP, IRQ)
+!NCF        ELSE
+!NCF          CALL swn_outnc_openblockfile(FILENM, MYK, MXK,
+!NCF     &                                 OVLNAM, VOQ(:,VOQR(1)),
+!NCF     &                                 VOQ(:,VOQR(2)),
+!NCF     &                                 OQI, OQR, IVTYP, IRQ)
+!NCF        END IF
```

(`XCGRID + XOFFS`, as `SWCOLBLK` does: SWAN stores coordinates relative to an
offset.) Other frames keep `XP`, `YP`, which have no exception values there.

## output_obstacle_flags: output between grid points went missing at random

For each output point, SWAN allocates `CROSS(4,MIP)`: one flag per grid
corner saying whether an obstacle lies between the point and that corner.
`SWIPOL` leaves a corner out of the interpolation when its flag is true. In
this SWAN version the flags are allocated but never set: the line that should
compute them is commented out, and nothing else assigns them. So each flag held
whatever was in that memory before. Where it read "true", the corner was
dropped; with all four dropped, the output was the exception value (-9 for Hs,
-99 for depth). `FRAME`, `POINTS`/`TABLE`, `CURVE` and `SPECOUT` values between
grid points were affected, differently from run to run: in one test 4 of 9
`TABLE` points were missing, in the next run a different set. Output on the
grid points themselves (`BLOCK 'COMPGRID'`, and what the coupler uses) was not
affected, because no interpolation is needed there.

**The fix** sets the flags to "false" right after each of the three
allocations:

```fortran
         ALLOCATE(CROSS(4,MIP))
+        CROSS = .FALSE.
```

Cases with obstacles: SWAN still does not account for obstacles when it
interpolates output, as before (the computation itself does).

## How the test works

`tests/fixes/swan-output-fixes/run.sh` ([README](../../../../tests/fixes/swan-output-fixes/README.md))
runs stock Inlet_test for 1 h before and after the patch, with 1 and with 2
SWAN processes, plus 9 output points between grid points written both as a
text `TABLE` and as a NetCDF `TABLE`. Two details make the bugs show reliably:

- the 9 points lie between grid points, so their values need interpolation
  (and therefore the obstacle flags);
- `MALLOC_PERTURB_` (a glibc setting) fills newly allocated memory with a
  non-zero byte pattern, so the uninitialised flags of `output_obstacle_flags`
  read "true" every time instead of at random. Correctly initialised memory is
  not affected by it.

`check.py` then checks:

- `table_nc_coordinates`: the NetCDF table from 2 SWAN processes has the
  points' coordinates;
- `compgrid_nc_coordinates`: `hsig.nc` from 1 SWAN process has no -1e10
  coordinates;
- `output_obstacle_flags`: no missing values in the text table, with 1 or 2
  processes.

## Engine test results

Run 2026-10-30 on the control VM, stock Inlet_test, 1 h, with
`MALLOC_PERTURB_=85`; "before" is the series up to this patch, "after" adds it.
PASS:

```
== before the patch
table_nc_coordinates     TABLE .nc, 2 SWAN: point coordinates      x[0..2] = 0, 200, 400        BAD
compgrid_nc_coordinates  BLOCK COMPGRID .nc, 1 SWAN: x/y exception 211 points at -1e10          BAD
output_obstacle_flags    TABLE text between grid points, 1 SWAN    53 of 63 values = -9         BAD
output_obstacle_flags    TABLE text between grid points, 2 SWAN    56 of 63 values = -9         BAD
== after the patch
table_nc_coordinates     TABLE .nc, 2 SWAN: point coordinates      x[0..2] = 4930, 5070, 5210   ok
compgrid_nc_coordinates  BLOCK COMPGRID .nc, 1 SWAN: x/y exception 0 points at -1e10            ok
output_obstacle_flags    TABLE text between grid points, 1 SWAN    0 of 63 values = -9          ok
output_obstacle_flags    TABLE text between grid points, 2 SWAN    0 of 63 values = -9          ok
```

`table_nc_coordinates` before: the 9 points got the x coordinates of the first
grid cells (0, 200, 400 m, ...) instead of 4930, 5070, 5210 m.
`output_obstacle_flags` before: with every flag reading "true", most values
between grid points are missing (why a few are not was not traced); without
`MALLOC_PERTURB_` the number missing varies from run to run (4 of 9 points in
the original finding). Wall time 57-69 s per run, the same before and after.

## Who is affected

- `table_nc_coordinates`: NetCDF `TABLE` output with more than one SWAN
  process.
- `compgrid_nc_coordinates`: NetCDF `BLOCK 'COMPGRID'` output with one SWAN
  process on a grid with inactive points.
- `output_obstacle_flags`: any output between grid points (`FRAME`, `POINTS`,
  `CURVE`, `SPECOUT`), at random.
