"""Run checks for 1-fixes/swan-vegetation-fixes.patch on Veg_test.

    python -I check_runs.py RUN_SUBMERGED RUN_EMERGENT INIT_EMERGENT

The two runs use SWAN's VEGETATION 3 (COAWST's SVEG_COAWST, drag method 1:
Cd = 1) and write the drag coefficient it uses (DICD, dicd.mat) and the depth
(depth.mat) every 5 min. Checks, at every output after the first computation:
  item 17  DICD is written (not all zero)
  item 16  where plants are taller than the water is deep (emergent run),
           Cd follows the drag method (1), not a fixed 1.95
Exit 0 if all checks pass.
"""
import sys

import numpy as np
import scipy.io as sio
from netCDF4 import Dataset

sub, eme, init = sys.argv[1:4]
ok = True


def fields(path, prefix):
    m = sio.loadmat(path)
    return [m[k] for k in sorted(k for k in m if k.lower().startswith(prefix))][1:]  # skip t = 0


def report(item, what, good, detail):
    global ok
    ok &= good
    print(f"item {item:3s} {what:52s} {detail:36s} {'ok' if good else 'BAD'}")


for run, label in ((sub, "submerged plants"), (eme, "emergent plants")):
    cd = fields(f"{run}/dicd.mat", "dicd")
    vals = np.unique(np.round(np.concatenate([c[np.isfinite(c)].ravel() for c in cd]), 4))
    report("17", f"DICD written, {label}", bool(cd) and vals.max() > 0, f"values {vals[:4].tolist()}")
d = Dataset(init)
height = np.asarray(d["plant_height"][0, 0])
dens = np.asarray(d["plant_density"][0, 0])
dep = fields(f"{eme}/depth.mat", "depth")[-1]
cd = fields(f"{eme}/dicd.mat", "dicd")[-1]
emergent = (dens > 0) & (height > dep[: height.shape[0], : height.shape[1]])
cde = cd[: height.shape[0], : height.shape[1]][emergent]
report("16", "Cd at emergent plants = 1 (drag method 1)",
       emergent.sum() > 0 and np.allclose(cde, 1.0), f"{int(emergent.sum())} points, Cd {np.unique(np.round(cde, 3))[:3].tolist()}")
print("ALL OK" if ok else "SOME CHECKS BAD")
sys.exit(0 if ok else 1)
