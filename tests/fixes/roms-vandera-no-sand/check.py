"""Check the roms-vandera-no-sand runs (see run.sh).

    python -I tests/fixes/roms-vandera-no-sand/check.py OUTDIR

OUTDIR holds diffgrid_before, diffgrid_after, inlet_before, inlet_after, each
with one ROMS history file (*his*.nc). Prints each check and exits 1 if one
fails. Needs numpy and netCDF4.
"""
import glob
import os
import sys

import numpy as np
from netCDF4 import Dataset

# Van der A fields copied from the arrays the patch sets (output names).
VANDERA = ["fd_wbl", "Ursell_number", "velocity_skewness", "acceleration_skewness",
           "Ucrest_wave", "Utrough_wave", "Tcrest_wave", "Ttrough_wave"]


def his(out, run):
    files = sorted(glob.glob(os.path.join(out, run, "*his*.nc")))
    if not files:
        sys.exit(f"check: no history file in {run}")
    d = Dataset(files[0])
    d.set_auto_mask(False)
    return d


def water(d, a):
    """Values of a 2-D field (time, eta, xi) at water points."""
    m = d["mask_rho"][:] > 0 if "mask_rho" in d.variables else np.ones(a.shape[-2:], bool)
    return a[..., m]


def main(out):
    ok = True

    def report(name, passed, detail):
        nonlocal ok
        ok &= passed
        print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")

    b, a = his(out, "diffgrid_before"), his(out, "diffgrid_after")
    present = [v for v in VANDERA if v in a.variables]
    print(f"DiffGrid (mud only), van der A fields written: {', '.join(present)}")
    fb = water(b, b["fd_wbl"][:])
    report("DiffGrid before: fd_wbl unset (NaN)", bool(np.isnan(fb).any()),
           f"{int(np.isnan(fb).sum())} of {fb.size} water values NaN")
    for v in present:
        x = water(a, a[v][:])
        report(f"DiffGrid after: {v} is zero", bool(np.all(x == 0)),
               f"{int(np.isnan(x).sum())} NaN, largest |value| {np.nanmax(np.abs(x)):.3g}")
    same = [v for v in b.variables if v in a.variables and v not in VANDERA]
    differ = [v for v in same if not np.array_equal(b[v][:], a[v][:], equal_nan=True)]
    report("DiffGrid: every other variable bit-identical before vs after", not differ,
           f"{len(same)} compared" + (f"; differ: {', '.join(differ)}" if differ else ""))

    b, a = his(out, "inlet_before"), his(out, "inlet_after")
    same = [v for v in b.variables if v in a.variables]
    differ = [v for v in same if not np.array_equal(b[v][:], a[v][:], equal_nan=True)]
    report("Inlet_test Coupled (sand): every variable bit-identical before vs after", not differ,
           f"{len(same)} compared, fd_wbl {'in' if 'fd_wbl' in same else 'not in'} the file"
           + (f"; differ: {', '.join(differ)}" if differ else ""))
    return ok


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(0 if main(sys.argv[1]) else 1)
