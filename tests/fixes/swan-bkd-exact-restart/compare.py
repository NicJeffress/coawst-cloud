"""Compare a restarted segment's history with the straight run, every variable, bit for bit.

Usage: python -I compare.py STRAIGHT/ocean_his.nc SEGMENT/ocean_his.nc

For each record of the segment that the straight run also has: the variables that differ and
their largest absolute difference (+0.0 first, so that -0 does not count as different).
"""
import sys

import netCDF4
import numpy as np

a = netCDF4.Dataset(sys.argv[1])
b = netCDF4.Dataset(sys.argv[2])
ta = a["ocean_time"][:]
for ib, t in enumerate(b["ocean_time"][:]):
    match = np.where(np.abs(ta - t) < 0.1)[0]
    if not len(match):
        continue
    diff = {}
    for name, v in b.variables.items():
        if "ocean_time" not in v.dimensions or v.dtype.kind != "f" or name == "ocean_time" or name not in a.variables:
            continue
        x = np.ma.filled(a[name][match[0]], np.nan).astype(float) + 0.0
        y = np.ma.filled(v[ib], np.nan).astype(float) + 0.0
        if not np.array_equal(x, y, equal_nan=True):
            diff[name] = float(np.nanmax(np.abs(x - y)))
    print(f"t = {t / 3600:7.3f} h:", diff or "bit-identical")
