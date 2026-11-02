#!/bin/bash
# Build the engine image of COAWST's Inlet_test and run it for one hour.
#
#   tests/ci/inlet_smoke.sh OUTDIR [HOURS]
#
# A quick end-to-end check that the patched COAWST builds and runs coupled:
# ROMS on 1x2 tiles + 1 SWAN process (3 MPI processes), HOURS simulated
# (default 1). PASS if the run finishes and ROMS's history file has no NaN.
# Needs Docker and Python with numpy and netCDF4 (PYTHON, default python3).
# About 10 minutes on 4 vCPUs, most of it the build.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$(realpath -m "${1:?usage: inlet_smoke.sh OUTDIR [HOURS]}")
HOURS=${2:-1}
PY=${PYTHON:-python3}
mkdir -p "$out"
"$root/build/coawst/build.sh" --tag coawst:ci-inlet
"$root/tests/tools/run_inlet.sh" coawst:ci-inlet "$out" inlet 1 2 1 "$HOURS"
"$PY" -I - "$out/inlet" <<'PYEOF'
import glob, sys
import numpy as np
from netCDF4 import Dataset
files = sorted(glob.glob(sys.argv[1] + "/*his*.nc"))
if not files:
    sys.exit("FAIL  no ROMS history file")
with Dataset(files[0]) as d:
    n = len(d.dimensions["ocean_time"])
    bad = [v for v in ("zeta", "ubar", "vbar", "u", "v") if v in d.variables
           and not np.isfinite(np.ma.filled(d[v][:].astype(float), 0.0)).all()]
    hs = d["Hwave"][-1] if "Hwave" in d.variables else None
print(f"{'FAIL' if bad else 'PASS'}  Inlet_test: {n} history records"
      + (f", NaN in {', '.join(bad)}" if bad else ", no NaN")
      + (f"; Hwave at the end {float(hs.max()):.2f} m at most" if hs is not None else ""))
sys.exit(1 if bad else 0)
PYEOF
