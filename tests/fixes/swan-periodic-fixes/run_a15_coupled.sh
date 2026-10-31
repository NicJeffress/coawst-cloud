#!/bin/bash
# Coupled test of periodic_coupled_stokes (1-fixes/swan-periodic-fixes.patch):
# in a coupled periodic run, SWAN must send ROMS the spectral Stokes fields of
# the right grid points.
#
#   tests/fixes/swan-periodic-fixes/run_a15_coupled.sh SOURCE OUTDIR [MINUTES]
#
# SOURCE: a COAWST tree or tarball at the pinned commit (to regenerate SWAN's
# patches without the change). Case: tests/cases/Reef_Ideal_A15 (ROMS and SWAN
# periodic, spectral Stokes drift), MINUTES simulated (default 60), ROMS 1x2 +
# 2 SWAN, history every 10 min. A15's periodic curvilinear SWAN grid and its
# NetCDF output need two improvements, which both builds borrow:
#   series = the fixes in patches/series + 2-improvements/swan-netcdf-output
#            + 2-improvements/swan-periodic-curvilinear
#   before: SWAN patches regenerated without periodic_coupled_stokes
#   after:  the patches as they are
# Expected: before, the spectra of row j reach ROMS shifted by j-1 columns: the
# pass's spectra land on the crest, the Stokes drift there is far too strong and
# ROMS may blow up (2026-10-21: 1.4 m/s, blow-up after 35 min); after, the run
# finishes with Stokes drift of the order of 0.1 m/s.
# STAGES (default "build run check"): e.g. STAGES=build, run the two cases
# elsewhere into OUTDIR/before and OUTDIR/after, then STAGES=check.
# Needs Docker and Python with numpy and netCDF4 (PYTHON). About 40 min.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
tools=$here/../../tools
build=$here/../../../build/coawst/build.sh
SRC=$1 OUT=$(realpath -m "$2") MIN=${3:-60}
PY=${PYTHON:-python3}
mkdir -p "$OUT"
STAGES=${STAGES:-build run check}
has() { [[ " $STAGES " == *" $1 "* ]]; }
if has build; then
{ grep -vE '^[[:space:]]*(#|$)' "$here/../../../build/coawst/patches/series" | grep '^1-fixes/'
  echo 2-improvements/swan-netcdf-output.patch
  echo 2-improvements/swan-periodic-curvilinear.patch; } > "$OUT/series"
"$tools/variant_patches.sh" "$SRC" "$OUT/patches-without" periodic_coupled_stokes | tail -1
case_args=(--case "$here/../../cases/Reef_Ideal_A15" --app REEF_IDEAL_A15 --series "$OUT/series")
"$build" "${case_args[@]}" --patch-dir "$OUT/patches-without" --tag coawst-test:a15stokes-before > "$OUT/build-before.log" 2>&1
"$build" "${case_args[@]}" --tag coawst-test:a15stokes-after > "$OUT/build-after.log" 2>&1
fi
if has run; then
for side in before after; do
    OUTDT=10 "$tools/run_case.sh" coawst-test:a15stokes-$side "$OUT" $side Reef_Ideal_A15 1 2 2 "$MIN" || true
done
fi
has check || exit 0
"$PY" -I - "$OUT" "$MIN" <<'EOF' | tee "$OUT/check.txt"
import sys
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
out = Path(sys.argv[1]); ok = True
for side in ("before", "after"):
    log = (out / side / "log.txt").read_text(errors="replace")
    blew = "Blowing-up" in log or "BLOWUP" in log.upper()
    his = out / side / "output" / "ocean_his.nc"
    d = Dataset(his); t = d["ocean_time"][:] / 60.0
    us = np.ma.filled(d["u_stokes"][:], np.nan); vs = np.ma.filled(d["v_stokes"][:], np.nan)
    smax = [float(np.nanmax(np.abs(np.concatenate([us[k].ravel(), vs[k].ravel()])))) for k in range(len(t))]
    print(f"{side:6s}: blow-up {'yes' if blew else 'no'}, records at {', '.join(f'{x:.0f}' for x in t)} min, "
          f"max |Stokes drift| per record: {', '.join(f'{x:.3f}' for x in smax)} m/s")
    if side == "before":
        ok &= blew or max(smax) > 0.5
    else:
        ok &= not blew and t[-1] >= float(sys.argv[2]) - 0.5 and max(smax) < 0.5
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
EOF
