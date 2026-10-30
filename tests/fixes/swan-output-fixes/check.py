"""Checks for 1-fixes/swan-output-fixes.patch on Inlet_test runs.

    python -I check.py RUN_1SWAN RUN_2SWAN

RUN_1SWAN, RUN_2SWAN: run folders of tests/tools/run_inlet.sh with 1 and 2 SWAN
processes and the extra output of run.sh. Prints one line per check with the
numbers and "ok"/"BAD"; exit 0 if all are ok.
  item 6  TABLE ... 'pts.nc' with 2 SWAN processes: x, y are the output points
  item 7  BLOCK 'COMPGRID' hsig.nc with 1 SWAN process: x, y are the grid
          coordinates everywhere (no -1e10 exception values)
  item 14 TABLE text output at 9 points between grid points: no exception
          values (Hs -9) in any record, with 1 and with 2 SWAN processes
"""
import sys

import numpy as np
from netCDF4 import Dataset

PTS = [(x, y) for y in (9930.0, 10070.0, 10210.0) for x in (4930.0, 5070.0, 5210.0)]
one, two = sys.argv[1], sys.argv[2]
ok_all = True


def report(item, what, ok, detail):
    global ok_all
    ok_all &= ok
    print(f"item {item:3s} {what:58s} {detail:34s} {'ok' if ok else 'BAD'}")


# item 6
d = Dataset(f"{two}/pts.nc")
x, y = np.asarray(d["x"][:]).ravel(), np.asarray(d["y"][:]).ravel()
want_x, want_y = np.array([p[0] for p in PTS]), np.array([p[1] for p in PTS])
good = x.shape == want_x.shape and np.allclose(x, want_x) and np.allclose(y, want_y)
report("6", "TABLE .nc, 2 SWAN: point coordinates", good,
       f"x[0..2] = {', '.join(f'{v:g}' for v in x[:3])}")

# item 7
d = Dataset(f"{one}/hsig.nc")
xg = np.asarray(d["x"][:])
nbad = int((xg < -1e9).sum())
report("7", "BLOCK COMPGRID .nc, 1 SWAN: x/y exception values", nbad == 0, f"{nbad} points at -1e10")

# item 14
for run, label in ((one, "1 SWAN"), (two, "2 SWAN")):
    rows = [l.split() for l in open(f"{run}/pts.table") if l.strip() and not l.startswith("%")]
    hs = np.array([float(r[0]) for r in rows])
    nmiss = int((hs <= -8.99).sum())
    report("14", f"TABLE text between grid points, {label}: missing values", nmiss == 0,
           f"{nmiss} of {hs.size} values = -9")

print("ALL OK" if ok_all else "SOME CHECKS BAD")
sys.exit(0 if ok_all else 1)
