"""Checks for 2-improvements/swan-netcdf4-compression.patch.

    python -I check.py OUTDIR

OUTDIR from run.sh: before, after-classic, after (Inlet_test, 1 h). SWAN files
b_*.nc (BLOCK), pts.nc (TABLE), spec.nc (SPECOUT); ROMS ocean_his_coupled.nc.
Checks:
  format     before and after-classic: SWAN files classic; after: NetCDF-4
             with shuffle + deflate on every multi-dimensional variable and
             none on 1-D axes; ROMS NetCDF-4 in before and after
  values     every variable of every SWAN file identical in all three runs
             (data, missing points, attributes other than packing); ROMS
             history identical between before and after
  size       SWAN files smaller in after (reported)
"""
import glob
import os
import sys
from pathlib import Path

import numpy as np
from netCDF4 import Dataset

out = Path(sys.argv[1])
ok = True
RUNS = ("before", "after-classic", "after")


def check(name, good, text):
    global ok
    ok &= good
    print(f"{'ok ' if good else 'BAD'} {name}: {text}")


def swan_files(run):
    return sorted(os.path.basename(p) for p in glob.glob(str(out / run / "b_*.nc"))) + ["pts.nc", "spec.nc"]


def values(path):
    d = Dataset(path)
    d.set_auto_mask(False)
    return d, {v: d[v][:] for v in d.variables}


files = swan_files("before")
check("files", len(files) >= 8 and all(swan_files(r) == files for r in RUNS),
      f"{len(files)} SWAN files in each run: {', '.join(files)}")

# format and filters
fmt = {r: {f: Dataset(out / r / f).data_model for f in files} for r in RUNS}
for r, want in (("before", "NETCDF3_64BIT_OFFSET"), ("after-classic", "NETCDF3_64BIT_OFFSET"), ("after", "NETCDF4")):
    got = sorted(set(fmt[r].values()))
    check(f"format {r}", got == [want], f"SWAN files {', '.join(got)}")
comp, plain, wrong = 0, 0, []
for f in files:
    d = Dataset(out / "after" / f)
    for v in d.variables.values():
        flt = v.filters() or {}
        z = bool(flt.get("zlib")) and bool(flt.get("shuffle"))
        if v.ndim > 1:
            comp += z
            if not z:
                wrong.append(f"{f}:{v.name} not compressed")
        else:
            plain += 1
            if z:
                wrong.append(f"{f}:{v.name} 1-D compressed")
check("filters after", not wrong and comp > 0,
      f"{comp} multi-dimensional variables with shuffle + deflate, {plain} 1-D variables plain"
      + (f"; {', '.join(wrong[:4])}" if wrong else ""))
for r in ("before", "after"):
    m = Dataset(out / r / "ocean_his_coupled.nc").data_model
    check(f"ROMS format {r}", m == "NETCDF4", m)

# values: SWAN in all three runs, ROMS before vs after
bad = []
for f in files:
    ref, rv = values(out / "before" / f)
    for r in ("after-classic", "after"):
        d, xv = values(out / r / f)
        if rv.keys() != xv.keys():
            bad.append(f"{r}/{f}: variables differ")
            continue
        for v in rv:
            if not np.array_equal(rv[v], xv[v], equal_nan=True) or rv[v].dtype != xv[v].dtype:
                bad.append(f"{r}/{f}:{v}")
            ra = {k: str(ref[v].getncattr(k)) for k in ref[v].ncattrs()}
            xa = {k: str(d[v].getncattr(k)) for k in d[v].ncattrs()}
            if ra != xa:
                bad.append(f"{r}/{f}:{v} attributes")
n_var = sum(len(Dataset(out / "before" / f).variables) for f in files)
check("SWAN values", not bad, f"{n_var} variables in {len(files)} files identical in all three runs"
      if not bad else f"differ: {', '.join(bad[:6])}")
_, a = values(out / "before" / "ocean_his_coupled.nc")
_, b = values(out / "after" / "ocean_his_coupled.nc")
rbad = [v for v in a if not np.array_equal(a[v], b[v], equal_nan=True)]
check("ROMS values", not rbad and a.keys() == b.keys(), f"history: {len(a)} variables, {len(rbad)} differ")

# sizes
size = {r: sum(os.path.getsize(out / r / f) for f in files) for r in RUNS}
detail = ", ".join(f"{f} {os.path.getsize(out / 'before' / f) / 1e3:.0f} -> {os.path.getsize(out / 'after' / f) / 1e3:.0f} kB" for f in files)
check("size", size["after"] < size["before"],
      f"SWAN files {size['before'] / 1e6:.2f} MB (before) -> {size['after'] / 1e6:.2f} MB (after), "
      f"{size['before'] / size['after']:.1f}x smaller; {detail}")
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
