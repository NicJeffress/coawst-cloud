"""Run checks for 1-fixes/swan-periodic-fixes.patch (periodic_compgrid_frame and periodic_y_strips).

    python -I check_runs.py RUN_DIR

RUN_DIR holds standalone SWAN runs from run.sh (inputs: make_inputs.py),
<case>-np<N>/output/*.nc. Hs at the last output (1 h):
  periodic_y_strips  periodic grid with more points in x than in y ('wide', SWAN cuts it
           into x-strips): 4 processes must give the 1-process result
           ('tall', y-strips, is the control: fine before and after)
  periodic_compgrid_frame  BLOCK 'COMPGRID' output of a periodic grid must equal output on
           the grid points (FRAME), with no missing values
Exit 0 if all checks pass.
"""
import sys
from pathlib import Path

import netCDF4
import numpy as np

run = Path(sys.argv[1])
ok = True


def hs(case, name="hsign.nc"):
    f = run / case / "output" / name
    if not f.exists():
        return None
    with netCDF4.Dataset(f) as d:
        v = [v for v in d.variables.values() if v.ndim == 3][0]
        return np.ma.filled(v[-1].astype(float), np.nan)


def report(item, what, good, detail):
    global ok
    ok &= good
    print(f"{item:25s} {what:50s} {detail:42s} {'ok' if good else 'BAD'}")


for grid, label in (("wide", "x-strips"), ("tall", "y-strips, control")):
    a, b = hs(f"{grid}-rep-mid-np1"), hs(f"{grid}-rep-mid-np4")
    if b is None:
        report("periodic_y_strips", f"{grid} ({label}): 4 vs 1 SWAN processes", False, "4-process run failed (no output)")
        continue
    same = np.array_equal(a, b, equal_nan=True)
    diff = np.nanmax(np.abs(a - b)) if not same else 0.0
    report("periodic_y_strips", f"{grid} ({label}): 4 vs 1 SWAN processes", same,
           "bit-identical" if same else f"max |diff| {diff:.3g} m, Hs max {np.nanmax(b):.3g} m")
for grid in ("wide", "tall"):
    frame, cg = hs(f"{grid}-rep-mid-np1"), hs(f"{grid}-rep-mid-np1", "hsign_compgrid.nc")
    miss = int(np.isnan(cg).sum())
    same = cg.shape == frame.shape and np.allclose(cg, frame, equal_nan=True)
    report("periodic_compgrid_frame", f"{grid}: COMPGRID output vs output on grid points", same and miss == 0,
           f"{miss} of {cg.size} missing" + ("" if same else ", values differ"))
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
