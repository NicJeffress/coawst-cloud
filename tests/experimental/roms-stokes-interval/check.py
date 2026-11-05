#!/usr/bin/env python3
"""Compare two runs' history (and diagnostic) files record by record, at the times they share.

Usage: check.py BASE_DIR RUN_DIR [--tol 0]

Prints, for each shared record, how many fields differ and the largest. Use tol 0 for the
bit-identity checks: STOKES_NCPL 0 against a build without the patch, and a restarted run
against its straight twin.
"""
import argparse

import netCDF4
import numpy as np

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("base")
ap.add_argument("run")
ap.add_argument("--tol", type=float, default=0.0)
a = ap.parse_args()
bad = 0
for name in ("ocean_his.nc", "ocean_dia.nc"):
    try:
        b = netCDF4.Dataset(f"{a.base}/{name}")
        d = netCDF4.Dataset(f"{a.run}/{name}")
    except FileNotFoundError:
        continue
    b.set_auto_mask(False)
    d.set_auto_mask(False)
    tb = b["ocean_time"][:]
    for l, t in enumerate(d["ocean_time"][:]):
        k = int(np.argmin(np.abs(tb - t)))
        if tb[k] != t:
            continue
        diff = []
        n = 0
        for v in d.variables:
            if v in b.variables and d[v].dimensions[:1] == ("ocean_time",) and d[v].ndim >= 3:
                x = np.array(b[v][k], float)
                y = np.array(d[v][l], float)
                x[np.abs(x) > 1e30] = 0
                y[np.abs(y) > 1e30] = 0
                n += 1
                m = np.abs(x - y).max()
                if m > a.tol:
                    diff.append((v, float(f"{m:.2e}")))
        bad += bool(diff)
        print(f"{name} hour {t / 3600:g}: {n} fields, {len(diff)} differ {diff[:6]}")
print("records with differences:", bad)
