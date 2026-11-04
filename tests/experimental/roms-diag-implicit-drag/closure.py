"""Momentum budget closure from ocean_dia.nc: accel minus the sum of every term, 2-D and 3-D.

Usage: python closure.py DIA.nc
Terms are read from the file, so a missing term shows up as a residual.
"""
import sys

import netCDF4
import numpy as np

d = netCDF4.Dataset(sys.argv[1])
names = set(d.variables)
SUB = {"xadv", "yadv", "xvisc", "yvisc", "zeta", "zetaw", "zqsp", "zbeh", "accel"}  # parts of another term
for pre in ("ubar", "vbar", "u", "v"):
    terms = sorted(n for n in names if n.startswith(pre + "_") and n[len(pre) + 1:] not in SUB)
    print(f"{pre}: {[t[len(pre) + 1:] for t in terms]}")
    for it in range(d.dimensions["ocean_time"].size):
        acc = np.ma.filled(d[pre + "_accel"][it], np.nan).astype(float)
        tot = np.zeros_like(acc)
        big = 0.0
        sizes = {}
        for t in terms:
            a = np.ma.filled(d[t][it], np.nan).astype(float)
            a[np.abs(a) > 1e10] = np.nan
            tot += np.nan_to_num(a)
            sizes[t[len(pre) + 1:]] = float(np.nanmax(np.abs(a)))
            big = max(big, sizes[t[len(pre) + 1:]])
        acc[np.abs(acc) > 1e10] = np.nan
        r = tot - acc
        print(
            f"  rec {it} t={d['ocean_time'][it] / 3600:.2f} h: max|residual| {np.nanmax(np.abs(r)):.2e}, rms {np.sqrt(np.nanmean(r**2)):.2e}, "
            f"largest term {big:.2e}, "
            + " ".join(f"{k} {v:.1e}" for k, v in sizes.items() if k in ("bstr", "fveg", "vvisc"))
        )
