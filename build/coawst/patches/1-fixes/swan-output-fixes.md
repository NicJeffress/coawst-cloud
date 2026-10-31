# swan-output-fixes.patch: SWAN output at the wrong place, or missing

| | |
|---|---|
| **Type** | fix |
| **Changes results?** | output only: what is written changes, the wave computation does not |
| **Default** | on |
| **Files** | `SWAN/src/swanparll.ftn` (`table_nc_coordinates`), `SWAN/src/swanout2.ftn` (`compgrid_nc_coordinates`), `SWAN/src/swanout1.ftn` (`output_obstacle_flags`) |
| **Evidence** | Inlet_test with extra output requests: three checks bad before, all ok after (results below) |
| **Test** | [`tests/fixes/swan-output-fixes/run.sh`](../../../../tests/fixes/swan-output-fixes/run.sh) |
| **Upstream** | `table_nc_coordinates` is in SWAN 41.51 itself; none reported yet |

Three independent bugs in SWAN's output; none changes the computed waves, but
each makes output files wrong in ways that are easy to miss.

## `table_nc_coordinates`: TABLE output to NetCDF from several SWAN processes put every point at the grid origin

With more than one SWAN process, each process writes its piece of a `TABLE`
and `SWCOLBLK` merges them. For NetCDF tables it wrote the coordinates of the
first grid cells (`XGRDGL`) as the locations of the output points, so every
point came out at the same wrong place (x = 0, y = 0 for Inlet_test's point at
5000 m, 10000 m). The values themselves were right. An upstream SWAN 41.51 bug.

Fix: `SWCOLOUT` passes the output points' coordinates (`XP`, `YP`) to
`SWCOLBLK`, which uses them for `TABLE` files.

## `compgrid_nc_coordinates`: BLOCK output on the computational grid had x, y = -1e10 at inactive points with one SWAN process

With one process, `BLOCK 'COMPGRID' ... .nc` took the `x`/`y` variables from
SWAN's `XP`/`YP` output quantities, which are set to the exception value
(-1e10) at inactive points (land, or wherever the bottom has the exception
value: 211 points in Inlet_test). With several processes the same file gets
the grid coordinates. So the coordinate arrays depended on the number of
processes, and plotting the one-process file put land points far off the map.

Fix: with one process, `SWBLOK` writes the grid coordinates as well
(`XCGRID + XOFFS`, as `SWCOLBLK` does). Other output frames keep `XP`/`YP`,
which have no exception values there.

## `output_obstacle_flags`: output between grid points was randomly missing

To give a value at a point between grid points, `SWIPOL` interpolates from
the surrounding grid corners, leaving out corners that an obstacle separates
from the point. Which corners those are is stored in flags `CROSS(4,MIP)`,
allocated for every output point but never set in this SWAN version (the
initialisation is commented out and nothing else assigns them). So the flags
held whatever was in that memory: where it read "true", the corner was
dropped, and with all corners dropped the output was the exception value
(-9 for Hs, -99 for depth). `FRAME`, `POINTS`/`TABLE`, `CURVE` and `SPECOUT`
values between grid points were affected, differently from run to run: in one
test 4 of 9 `TABLE` points were missing, in the next run a different set.
Output on the grid points themselves (`BLOCK 'COMPGRID'`, which is also what
the coupler uses) was not affected.

Fix: set the flags to "false" after allocating them. Cases with obstacles:
SWAN still does not account for obstacles when interpolating output, as
before.

## Test

`tests/fixes/swan-output-fixes/run.sh` runs stock Inlet_test for 1 h before
and after the patch, with 1 and with 2 SWAN processes, plus 9 output points
between grid points written as a text `TABLE` and as a NetCDF `TABLE`.
`MALLOC_PERTURB_` (a glibc setting) fills newly allocated memory with a
non-zero pattern, so the uninitialised flags of `output_obstacle_flags` read "true" every time
instead of at random; correct code is not affected by it. `check.py` checks:

- `table_nc_coordinates`: the NetCDF table from 2 SWAN processes has the points' coordinates;
- `compgrid_nc_coordinates`: `hsig.nc` from 1 SWAN process has no -1e10 coordinates;
- `output_obstacle_flags`: no missing values in the text table, with 1 or 2 processes.

## Engine test results

Run 2026-10-30 on the control VM, stock Inlet_test, 1 h, with
`MALLOC_PERTURB_=85`; "before" is the series up to this patch, "after" adds it.
PASS:

```
== before the patch
table_nc_coordinates  TABLE .nc, 2 SWAN: point coordinates          x[0..2] = 0, 200, 400        BAD
compgrid_nc_coordinates  BLOCK COMPGRID .nc, 1 SWAN: x/y exception     211 points at -1e10          BAD
output_obstacle_flags  TABLE text between grid points, 1 SWAN        53 of 63 values = -9         BAD
output_obstacle_flags  TABLE text between grid points, 2 SWAN        56 of 63 values = -9         BAD
== after the patch
table_nc_coordinates  TABLE .nc, 2 SWAN: point coordinates          x[0..2] = 4930, 5070, 5210   ok
compgrid_nc_coordinates  BLOCK COMPGRID .nc, 1 SWAN: x/y exception     0 points at -1e10            ok
output_obstacle_flags  TABLE text between grid points, 1 SWAN        0 of 63 values = -9          ok
output_obstacle_flags  TABLE text between grid points, 2 SWAN        0 of 63 values = -9          ok
```

`table_nc_coordinates` before: the 9 points got the x coordinates of the first grid cells
(0, 200, 400 m, ...). `output_obstacle_flags` before: with every flag reading "true", most
values between grid points are missing (why a few are not was not traced);
without `MALLOC_PERTURB_` the number missing varies from run to run (4 of 9
points in the original finding).
Wall time 57-69 s per run, the same before and after.
