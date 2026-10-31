"""Checks for 2-improvements/swan-netcdf-output.patch.

    python -I check.py OUTDIR

OUTDIR from run.sh (Inlet_test, 1 h, each quantity requested both as
BLOCK .nc and as BLOCK .mat, written every 30 min):
  before-same  without the patch, the 7 quantities stock SWAN writes as .nc
  after-same   with it, the same requests
  after-all    with it, 25 quantities (the 7 plus 18 the patch adds)
  before-new   without it, DISSIP as .nc (stock SWAN refuses it)
Checks:
  unchanged    before-same and after-same: every .mat file and the ROMS
               history are bit-identical (the patch changes output only)
  precision    the .nc values against the .mat values of the same run:
               before, off by up to half the packing step; after, equal
  new          after-all: every .nc the patch adds equals its .mat
  refused      before-new: SWAN reports "netCDF output not allowed"
"""
import glob
import os
import re
import sys
import warnings
from pathlib import Path

import numpy as np
from netCDF4 import Dataset
from scipy.io import loadmat

warnings.simplefilter("ignore")        # scipy: duplicate names in BOTLEV .mat files
out = Path(sys.argv[1])
ok = True
# BLOCK keyword (lower case) -> NetCDF variable(s) and .mat prefix(es)
NC = {"depth": ["depth"], "watlev": ["ssh"], "botlev": ["botl"], "vel": ["xcur", "ycur"],
      "hsign": ["hs"], "rtp": ["tp"], "ubot": ["ubot"], "frcoef": ["fric"], "dissip": ["dissip"],
      "tmbot": ["tmbot"], "qb": ["qb"], "transp": ["xtra", "ytra"], "force": ["xfor", "yfor"],
      "steepness": ["steepness"], "per": ["per"], "rper": ["rper"], "ursell": ["ursell"],
      "disbot": ["disbot"], "dissurf": ["dissurf"], "diswcap": ["diswcap"], "generat": ["genera"],
      "redist": ["redist"], "propagat": ["propagat"], "radstr": ["radstr"], "tdir": ["tdir"]}
STOCK = ["depth", "watlev", "botlev", "vel", "hsign", "rtp", "ubot"]


def mat_fields(path):
    """{component: [field at each output time]} from a SWAN BLOCK .mat file."""
    m = {k: v for k, v in loadmat(path).items() if not k.startswith("__")}
    comps = {}
    for k in sorted(m):
        mm = re.match(r"(.*?)(_x|_y)?(_\d{8}_\d{6})?$", k)
        comps.setdefault(mm.group(2) or "", []).append(np.asarray(m[k], dtype=float))
    return [comps[c] for c in sorted(comps)]       # "" or ("_x", "_y")


def compare(run, q):
    """Largest |nc - mat| over all times and components, and whether the
    missing points agree. Exception values: .mat holds NaN or SWAN's
    exception value where the .nc is masked."""
    worst, same_mask, packed = 0.0, True, False
    ds = Dataset(run / f"n_{q}.nc")
    for var, fields in zip(NC[q], mat_fields(run / f"m_{q}.mat")):
        v = ds[var]
        packed |= "scale_factor" in v.ncattrs()
        nc = np.ma.filled(v[:].astype(float), np.nan)
        if len(fields) == 1 and nc.shape[0] > 1:  # time-independent (BOTLEV)
            nc = nc[-1:]
        for a, b in zip(nc, fields):
            good = np.isfinite(a) & np.isfinite(b) & (b > -9e3)
            same_mask &= int(np.sum(np.isfinite(a))) == int(np.sum(good))
            if good.any():
                worst = max(worst, float(np.max(np.abs(a[good] - b[good]))))
    return worst, same_mask, packed


def check(name, good, text):
    global ok
    ok &= good
    print(f"{'ok ' if good else 'BAD'} {name}: {text}")


# unchanged: .mat files and ROMS history, before vs after
a, b = out / "before-same", out / "after-same"
mats = sorted(os.path.basename(p) for p in glob.glob(str(a / "*.mat")))
diff = []
for f in mats:
    x = {k: v for k, v in loadmat(a / f).items() if not k.startswith("__")}
    y = {k: v for k, v in loadmat(b / f).items() if not k.startswith("__")}
    if x.keys() != y.keys() or any(not np.array_equal(x[k], y[k], equal_nan=True) for k in x):
        diff.append(f)
check("unchanged SWAN", not diff and len(mats) > 10,
      f"{len(mats)} .mat files, {len(diff)} differ" + (f" ({', '.join(diff)})" if diff else ""))
ha, hb = Dataset(a / "ocean_his_coupled.nc"), Dataset(b / "ocean_his_coupled.nc")
rdiff = [v for v in ha.variables if ha[v].dtype.kind == "f"
         and not np.array_equal(np.ma.filled(ha[v][:], np.nan), np.ma.filled(hb[v][:], np.nan), equal_nan=True)]
check("unchanged ROMS", not rdiff, f"history: {len(rdiff)} variables differ" + (f" ({', '.join(rdiff[:5])})" if rdiff else ""))

# precision: .nc against .mat in the same run (stock SWAN packed most
# quantities into 16-bit integers; a few, such as depth, were already float)
packed_before = 0
for q in STOCK:
    w0, m0, p0 = compare(a, q)
    w1, m1, p1 = compare(b, q)
    packed_before += p0
    check(f"precision {q:6s}", (w0 > 0 or not p0) and w1 == 0 and not p1 and m1,
          f"before {'packed' if p0 else 'float'}, max |nc - mat| {w0:.2e}; "
          f"after {'packed' if p1 else 'float'}, {w1:.2e}" + ("" if m1 else ", missing points differ"))

check("precision packed", packed_before >= 3, f"{packed_before} of {len(STOCK)} stock quantities were packed")

# new quantities
new = [q for q in NC if q not in STOCK]
bad = []
for q in new:
    try:
        w, m, p = compare(out / "after-all", q)
    except (FileNotFoundError, OSError) as e:
        bad.append(f"{q} (missing: {e})")
        continue
    if w != 0 or not m or p:
        bad.append(f"{q} ({w:.1e}{'' if m else ', mask'}{', packed' if p else ''})")
check("new quantities", not bad, f"{len(new) - len(bad)}/{len(new)} written as float and equal to .mat"
      + (f"; bad: {', '.join(bad)}" if bad else ""))

# refused before the patch
txt = "".join(open(p, errors="replace").read() for p in glob.glob(str(out / "before-new/PRINT*")))
check("refused before", "netCDF output not allowed" in txt,
      "stock SWAN: " + ("'netCDF output not allowed for n_dissip.nc', run stopped" if "not allowed" in txt else "no refusal found"))
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
